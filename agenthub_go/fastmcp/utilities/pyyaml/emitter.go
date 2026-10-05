package pyyaml

import (
	"fmt"
	"sort"
	"strings"
	"unicode/utf8"
)

// Emitter (emitter.py): the full state machine, ported so that the default dumper
// (canonical=False, indent=2, width=80, allow_unicode=False, line_break="\n",
// default_flow_style=False) produces byte-identical output.

type scalarAnalysis struct {
	scalar            string
	empty             bool
	multiline         bool
	allowFlowPlain    bool
	allowBlockPlain   bool
	allowSingleQuoted bool
	allowDoubleQuoted bool
	allowBlock        bool
}

type emitter struct {
	buf strings.Builder

	// Emitter is a state machine with a stack of states.
	states []func()
	state  func()

	// Current event and the event queue.
	events []event
	event  event

	// Current indentation level and the stack of previous indents (-1 mirrors None).
	indents []int
	indent  int

	// Flow level and contexts.
	flowLevel        int
	rootContext      bool
	sequenceContext  bool
	mappingContext   bool
	simpleKeyContext bool

	// Characteristics of the last emitted character.
	line       int
	column     int
	whitespace bool
	indention  bool

	openEnded bool

	canonical     bool
	allowUnicode  bool
	bestIndent    int
	bestWidth     int
	bestLineBreak string

	tagPrefixes map[string]string

	preparedAnchor string
	preparedTag    string

	analysis *scalarAnalysis
	style    string
	hasStyle bool
}

func newEmitter() *emitter {
	e := &emitter{
		indent:        -1,
		bestIndent:    2,
		bestWidth:     80,
		bestLineBreak: "\n",
		whitespace:    true,
		indention:     true,
		tagPrefixes:   map[string]string{},
	}
	e.state = e.expectStreamStart
	return e
}

func (e *emitter) emit(ev event) {
	e.events = append(e.events, ev)
	for !e.needMoreEvents() {
		e.event = e.events[0]
		e.events = e.events[1:]
		e.state()
		e.event = nil
	}
}

func (e *emitter) needMoreEvents() bool {
	if len(e.events) == 0 {
		return true
	}
	switch e.events[0].(type) {
	case documentStartEvent:
		return e.needEvents(1)
	case sequenceStartEvent:
		return e.needEvents(2)
	case mappingStartEvent:
		return e.needEvents(3)
	}
	return false
}

func (e *emitter) needEvents(count int) bool {
	level := 0
	for _, ev := range e.events[1:] {
		switch ev.(type) {
		case documentStartEvent, sequenceStartEvent, mappingStartEvent:
			level++
		case documentEndEvent, sequenceEndEvent, mappingEndEvent:
			level--
		case streamEndEvent:
			level = -1
		}
		if level < 0 {
			return false
		}
	}
	return len(e.events) < count+1
}

func (e *emitter) increaseIndent(flow, indentless bool) {
	e.indents = append(e.indents, e.indent)
	if e.indent < 0 {
		if flow {
			e.indent = e.bestIndent
		} else {
			e.indent = 0
		}
	} else if !indentless {
		e.indent += e.bestIndent
	}
}

func (e *emitter) popIndent() {
	e.indent = e.indents[len(e.indents)-1]
	e.indents = e.indents[:len(e.indents)-1]
}

func (e *emitter) pushState(f func()) { e.states = append(e.states, f) }

func (e *emitter) popState() func() {
	s := e.states[len(e.states)-1]
	e.states = e.states[:len(e.states)-1]
	return s
}

// Stream handlers.

func (e *emitter) expectStreamStart() {
	if _, ok := e.event.(streamStartEvent); ok {
		e.writeStreamStart()
		e.state = e.expectFirstDocumentStart
		return
	}
	panic(fmt.Sprintf("expected StreamStartEvent, but got %T", e.event))
}

func (e *emitter) expectNothing() {
	panic(fmt.Sprintf("expected nothing, but got %T", e.event))
}

// Document handlers.

func (e *emitter) expectFirstDocumentStart() { e.expectDocumentStart(true) }

func (e *emitter) expectDocumentStartState() { e.expectDocumentStart(false) }

func (e *emitter) expectDocumentStart(first bool) {
	switch e.event.(type) {
	case documentStartEvent:
		// event.version and event.tags are always None in the default dumper.
		e.tagPrefixes = map[string]string{"!": "!", "tag:yaml.org,2002:": "!!"}
		implicit := first && !e.checkEmptyDocument()
		if !implicit {
			e.writeIndent()
			e.writeIndicator("---", true, false, false)
		}
		e.state = e.expectDocumentRoot
	case streamEndEvent:
		if e.openEnded {
			e.writeIndicator("...", true, false, false)
			e.writeIndent()
		}
		e.writeStreamEnd()
		e.state = e.expectNothing
	default:
		panic(fmt.Sprintf("expected DocumentStartEvent, but got %T", e.event))
	}
}

func (e *emitter) expectDocumentEnd() {
	if _, ok := e.event.(documentEndEvent); !ok {
		panic(fmt.Sprintf("expected DocumentEndEvent, but got %T", e.event))
	}
	e.writeIndent()
	// event.explicit is always None in the default dumper.
	e.flushStream()
	e.state = e.expectDocumentStartState
}

func (e *emitter) expectDocumentRoot() {
	e.pushState(e.expectDocumentEnd)
	e.expectNode(true, false, false, false)
}

// Node handlers.

func (e *emitter) expectNode(root, sequence, mapping, simpleKey bool) {
	e.rootContext = root
	e.sequenceContext = sequence
	e.mappingContext = mapping
	e.simpleKeyContext = simpleKey
	switch ev := e.event.(type) {
	case aliasEvent:
		e.processAnchor("*")
		_ = ev
		e.state = e.popState()
	case scalarEvent:
		e.processAnchor("&")
		e.processTag()
		e.expectScalar()
	case sequenceStartEvent:
		e.processAnchor("&")
		e.processTag()
		if e.flowLevel > 0 || e.canonical || ev.flowStyle || e.checkEmptySequence() {
			e.expectFlowSequence()
		} else {
			e.expectBlockSequence()
		}
	case mappingStartEvent:
		e.processAnchor("&")
		e.processTag()
		if e.flowLevel > 0 || e.canonical || ev.flowStyle || e.checkEmptyMapping() {
			e.expectFlowMapping()
		} else {
			e.expectBlockMapping()
		}
	default:
		panic(fmt.Sprintf("expected NodeEvent, but got %T", e.event))
	}
}

func (e *emitter) expectScalar() {
	e.increaseIndent(true, false)
	e.processScalar()
	e.popIndent()
	e.state = e.popState()
}

// Flow sequence handlers.

func (e *emitter) expectFlowSequence() {
	e.writeIndicator("[", true, true, false)
	e.flowLevel++
	e.increaseIndent(true, false)
	e.state = e.expectFirstFlowSequenceItem
}

func (e *emitter) expectFirstFlowSequenceItem() {
	if _, ok := e.event.(sequenceEndEvent); ok {
		e.popIndent()
		e.flowLevel--
		e.writeIndicator("]", false, false, false)
		e.state = e.popState()
		return
	}
	if e.canonical || e.column > e.bestWidth {
		e.writeIndent()
	}
	e.pushState(e.expectFlowSequenceItem)
	e.expectNode(false, true, false, false)
}

func (e *emitter) expectFlowSequenceItem() {
	if _, ok := e.event.(sequenceEndEvent); ok {
		e.popIndent()
		e.flowLevel--
		if e.canonical {
			e.writeIndicator(",", false, false, false)
			e.writeIndent()
		}
		e.writeIndicator("]", false, false, false)
		e.state = e.popState()
		return
	}
	e.writeIndicator(",", false, false, false)
	if e.canonical || e.column > e.bestWidth {
		e.writeIndent()
	}
	e.pushState(e.expectFlowSequenceItem)
	e.expectNode(false, true, false, false)
}

// Flow mapping handlers.

func (e *emitter) expectFlowMapping() {
	e.writeIndicator("{", true, true, false)
	e.flowLevel++
	e.increaseIndent(true, false)
	e.state = e.expectFirstFlowMappingKey
}

func (e *emitter) expectFirstFlowMappingKey() {
	if _, ok := e.event.(mappingEndEvent); ok {
		e.popIndent()
		e.flowLevel--
		e.writeIndicator("}", false, false, false)
		e.state = e.popState()
		return
	}
	if e.canonical || e.column > e.bestWidth {
		e.writeIndent()
	}
	if !e.canonical && e.checkSimpleKey() {
		e.pushState(e.expectFlowMappingSimpleValue)
		e.expectNode(false, false, true, true)
	} else {
		e.writeIndicator("?", true, false, false)
		e.pushState(e.expectFlowMappingValue)
		e.expectNode(false, false, true, false)
	}
}

func (e *emitter) expectFlowMappingKey() {
	if _, ok := e.event.(mappingEndEvent); ok {
		e.popIndent()
		e.flowLevel--
		if e.canonical {
			e.writeIndicator(",", false, false, false)
			e.writeIndent()
		}
		e.writeIndicator("}", false, false, false)
		e.state = e.popState()
		return
	}
	e.writeIndicator(",", false, false, false)
	if e.canonical || e.column > e.bestWidth {
		e.writeIndent()
	}
	if !e.canonical && e.checkSimpleKey() {
		e.pushState(e.expectFlowMappingSimpleValue)
		e.expectNode(false, false, true, true)
	} else {
		e.writeIndicator("?", true, false, false)
		e.pushState(e.expectFlowMappingValue)
		e.expectNode(false, false, true, false)
	}
}

func (e *emitter) expectFlowMappingSimpleValue() {
	e.writeIndicator(":", false, false, false)
	e.pushState(e.expectFlowMappingKey)
	e.expectNode(false, false, true, false)
}

func (e *emitter) expectFlowMappingValue() {
	if e.canonical || e.column > e.bestWidth {
		e.writeIndent()
	}
	e.writeIndicator(":", true, false, false)
	e.pushState(e.expectFlowMappingKey)
	e.expectNode(false, false, true, false)
}

// Block sequence handlers.

func (e *emitter) expectBlockSequence() {
	indentless := e.mappingContext && !e.indention
	e.increaseIndent(false, indentless)
	e.state = e.expectFirstBlockSequenceItem
}

func (e *emitter) expectFirstBlockSequenceItem() { e.expectBlockSequenceItem(true) }

func (e *emitter) expectBlockSequenceItemState() { e.expectBlockSequenceItem(false) }

func (e *emitter) expectBlockSequenceItem(first bool) {
	if !first {
		if _, ok := e.event.(sequenceEndEvent); ok {
			e.popIndent()
			e.state = e.popState()
			return
		}
	}
	e.writeIndent()
	e.writeIndicator("-", true, false, true)
	e.pushState(e.expectBlockSequenceItemState)
	e.expectNode(false, true, false, false)
}

// Block mapping handlers.

func (e *emitter) expectBlockMapping() {
	e.increaseIndent(false, false)
	e.state = e.expectFirstBlockMappingKey
}

func (e *emitter) expectFirstBlockMappingKey() { e.expectBlockMappingKey(true) }

func (e *emitter) expectBlockMappingKeyState() { e.expectBlockMappingKey(false) }

func (e *emitter) expectBlockMappingKey(first bool) {
	if !first {
		if _, ok := e.event.(mappingEndEvent); ok {
			e.popIndent()
			e.state = e.popState()
			return
		}
	}
	e.writeIndent()
	if e.checkSimpleKey() {
		e.pushState(e.expectBlockMappingSimpleValue)
		e.expectNode(false, false, true, true)
	} else {
		e.writeIndicator("?", true, false, true)
		e.pushState(e.expectBlockMappingValue)
		e.expectNode(false, false, true, false)
	}
}

func (e *emitter) expectBlockMappingSimpleValue() {
	e.writeIndicator(":", false, false, false)
	e.pushState(e.expectBlockMappingKeyState)
	e.expectNode(false, false, true, false)
}

func (e *emitter) expectBlockMappingValue() {
	e.writeIndent()
	e.writeIndicator(":", true, false, true)
	e.pushState(e.expectBlockMappingKeyState)
	e.expectNode(false, false, true, false)
}

// Checkers.

func (e *emitter) checkEmptySequence() bool {
	if _, ok := e.event.(sequenceStartEvent); !ok {
		return false
	}
	if len(e.events) == 0 {
		return false
	}
	_, ok := e.events[0].(sequenceEndEvent)
	return ok
}

func (e *emitter) checkEmptyMapping() bool {
	if _, ok := e.event.(mappingStartEvent); !ok {
		return false
	}
	if len(e.events) == 0 {
		return false
	}
	_, ok := e.events[0].(mappingEndEvent)
	return ok
}

func (e *emitter) checkEmptyDocument() bool {
	if _, ok := e.event.(documentStartEvent); !ok || len(e.events) == 0 {
		return false
	}
	ev, ok := e.events[0].(scalarEvent)
	if !ok {
		return false
	}
	return ev.anchor == "" && ev.tag == "" && ev.value == ""
}

func (e *emitter) checkSimpleKey() bool {
	length := 0
	switch e.event.(type) {
	case scalarEvent, sequenceStartEvent, mappingStartEvent:
		if e.preparedTag == "" {
			e.preparedTag = e.prepareTag(eventTag(e.event))
		}
		length += utf8.RuneCountInString(e.preparedTag)
	}
	if ev, ok := e.event.(scalarEvent); ok {
		if e.analysis == nil {
			e.analysis = e.analyzeScalar(ev.value)
		}
		length += utf8.RuneCountInString(e.analysis.scalar)
		return length < 128 && (!e.analysis.empty && !e.analysis.multiline)
	}
	// AliasEvent / empty collections / non-empty collections.
	isAlias := false
	if _, ok := e.event.(aliasEvent); ok {
		isAlias = true
	}
	return length < 128 && (isAlias || e.checkEmptySequence() || e.checkEmptyMapping())
}

func eventTag(ev event) string {
	switch v := ev.(type) {
	case scalarEvent:
		return v.tag
	case sequenceStartEvent:
		return v.tag
	case mappingStartEvent:
		return v.tag
	}
	return ""
}

// Anchor, Tag, and Scalar processors.

func (e *emitter) processAnchor(indicator string) {
	var anchor string
	switch v := e.event.(type) {
	case scalarEvent:
		anchor = v.anchor
	case sequenceStartEvent:
		anchor = v.anchor
	case mappingStartEvent:
		anchor = v.anchor
	case aliasEvent:
		anchor = v.anchor
	}
	if anchor == "" {
		e.preparedAnchor = ""
		return
	}
	if e.preparedAnchor == "" {
		e.preparedAnchor = e.prepareAnchor(anchor)
	}
	if e.preparedAnchor != "" {
		e.writeIndicator(indicator+e.preparedAnchor, true, false, false)
	}
	e.preparedAnchor = ""
}

func (e *emitter) processTag() {
	tag := ""
	switch v := e.event.(type) {
	case scalarEvent:
		tag = v.tag
		if !e.hasStyle {
			e.style = e.chooseScalarStyle()
			e.hasStyle = true
		}
		if (!e.canonical || tag == "") &&
			((e.style == "" && v.implicit[0]) || (e.style != "" && v.implicit[1])) {
			e.preparedTag = ""
			return
		}
		if v.implicit[0] && tag == "" {
			tag = "!"
			e.preparedTag = ""
		}
	case sequenceStartEvent:
		if (!e.canonical || tag == "") && v.implicit {
			e.preparedTag = ""
			return
		}
	case mappingStartEvent:
		if (!e.canonical || tag == "") && v.implicit {
			e.preparedTag = ""
			return
		}
	default:
		return
	}
	if tag == "" {
		panic("tag is not specified")
	}
	if e.preparedTag == "" {
		e.preparedTag = e.prepareTag(tag)
	}
	if e.preparedTag != "" {
		e.writeIndicator(e.preparedTag, true, false, false)
	}
	e.preparedTag = ""
}

func (e *emitter) chooseScalarStyle() string {
	ev := e.event.(scalarEvent)
	if e.analysis == nil {
		e.analysis = e.analyzeScalar(ev.value)
	}
	if ev.style == "\"" || e.canonical {
		return "\""
	}
	if ev.style == "" && ev.implicit[0] {
		if !(e.simpleKeyContext && (e.analysis.empty || e.analysis.multiline)) &&
			((e.flowLevel > 0 && e.analysis.allowFlowPlain) ||
				(e.flowLevel == 0 && e.analysis.allowBlockPlain)) {
			return ""
		}
	}
	if ev.style != "" && strings.ContainsAny(ev.style, "|>") {
		if e.flowLevel == 0 && !e.simpleKeyContext && e.analysis.allowBlock {
			return ev.style
		}
	}
	if ev.style == "" || ev.style == "'" {
		if e.analysis.allowSingleQuoted && !(e.simpleKeyContext && e.analysis.multiline) {
			return "'"
		}
	}
	return "\""
}

func (e *emitter) processScalar() {
	ev := e.event.(scalarEvent)
	if e.analysis == nil {
		e.analysis = e.analyzeScalar(ev.value)
	}
	if !e.hasStyle {
		e.style = e.chooseScalarStyle()
		e.hasStyle = true
	}
	split := !e.simpleKeyContext
	switch e.style {
	case "\"":
		e.writeDoubleQuoted(e.analysis.scalar, split)
	case "'":
		e.writeSingleQuoted(e.analysis.scalar, split)
	default:
		e.writePlain(e.analysis.scalar, split)
	}
	e.analysis = nil
	e.style = ""
	e.hasStyle = false
}

// Analyzers.

func (e *emitter) prepareTag(tag string) string {
	if tag == "" {
		panic("tag must not be empty")
	}
	if tag == "!" {
		return tag
	}
	handle := ""
	suffix := tag
	prefixes := make([]string, 0, len(e.tagPrefixes))
	for prefix := range e.tagPrefixes {
		prefixes = append(prefixes, prefix)
	}
	sort.Strings(prefixes)
	for _, prefix := range prefixes {
		if strings.HasPrefix(tag, prefix) && (prefix == "!" || len(prefix) < len(tag)) {
			handle = e.tagPrefixes[prefix]
			suffix = tag[len(prefix):]
		}
	}
	var chunks []string
	start, end := 0, 0
	for end < len(suffix) {
		ch := suffix[end]
		if (ch >= '0' && ch <= '9') || (ch >= 'A' && ch <= 'Z') || (ch >= 'a' && ch <= 'z') ||
			strings.IndexByte("-;/?:@&=+$,_.~*'()[]", ch) >= 0 ||
			(ch == '!' && handle != "!") {
			end++
		} else {
			if start < end {
				chunks = append(chunks, suffix[start:end])
			}
			start = end + 1
			end = start
			for _, b := range []byte{ch} {
				chunks = append(chunks, fmt.Sprintf("%%%02X", b))
			}
		}
	}
	if start < end {
		chunks = append(chunks, suffix[start:end])
	}
	suffixText := strings.Join(chunks, "")
	if handle != "" {
		return handle + suffixText
	}
	return "!<" + suffixText + ">"
}

func (e *emitter) prepareAnchor(anchor string) string {
	if anchor == "" {
		panic("anchor must not be empty")
	}
	for _, ch := range anchor {
		if !((ch >= '0' && ch <= '9') || (ch >= 'A' && ch <= 'Z') || (ch >= 'a' && ch <= 'z') ||
			ch == '-' || ch == '_') {
			panic(fmt.Sprintf("invalid character %q in the anchor: %q", ch, anchor))
		}
	}
	return anchor
}

func isScalarWhitespace(r rune) bool {
	switch r {
	case '\x00', ' ', '\t', '\r', '\n', '\u0085', '\u2028', '\u2029':
		return true
	}
	return false
}

func isScalarLineBreak(r rune) bool {
	switch r {
	case '\n', '\u0085', '\u2028', '\u2029':
		return true
	}
	return false
}

func (e *emitter) analyzeScalar(scalar string) *scalarAnalysis {
	if scalar == "" {
		return &scalarAnalysis{
			scalar: scalar, empty: true, multiline: false,
			allowFlowPlain: false, allowBlockPlain: true,
			allowSingleQuoted: true, allowDoubleQuoted: true, allowBlock: false,
		}
	}

	blockIndicators := false
	flowIndicators := false
	lineBreaks := false
	specialCharacters := false

	leadingSpace := false
	leadingBreak := false
	trailingSpace := false
	trailingBreak := false
	breakSpace := false
	spaceBreak := false

	rs := []rune(scalar)

	if strings.HasPrefix(scalar, "---") || strings.HasPrefix(scalar, "...") {
		blockIndicators = true
		flowIndicators = true
	}

	precededByWhitespace := true
	followedByWhitespace := len(rs) == 1 || isScalarWhitespace(rs[1])
	previousSpace := false
	previousBreak := false

	index := 0
	for index < len(rs) {
		ch := rs[index]

		if index == 0 {
			if strings.ContainsRune("#,[]{}&*!|>'\"%@`", ch) {
				flowIndicators = true
				blockIndicators = true
			}
			if ch == '?' || ch == ':' {
				flowIndicators = true
				if followedByWhitespace {
					blockIndicators = true
				}
			}
			if ch == '-' && followedByWhitespace {
				flowIndicators = true
				blockIndicators = true
			}
		} else {
			if strings.ContainsRune(",?[]{}", ch) {
				flowIndicators = true
			}
			if ch == ':' {
				flowIndicators = true
				if followedByWhitespace {
					blockIndicators = true
				}
			}
			if ch == '#' && precededByWhitespace {
				flowIndicators = true
				blockIndicators = true
			}
		}

		if isScalarLineBreak(ch) {
			lineBreaks = true
		}
		if !(ch == '\n' || (ch >= 0x20 && ch <= 0x7E)) {
			if (ch == 0x85 || (ch >= 0xA0 && ch <= 0xD7FF) || (ch >= 0xE000 && ch <= 0xFFFD) ||
				(ch >= 0x10000 && ch < 0x10FFFF)) && ch != 0xFEFF {
				if !e.allowUnicode {
					specialCharacters = true
				}
			} else {
				specialCharacters = true
			}
		}

		if ch == ' ' {
			if index == 0 {
				leadingSpace = true
			}
			if index == len(rs)-1 {
				trailingSpace = true
			}
			if previousBreak {
				breakSpace = true
			}
			previousSpace = true
			previousBreak = false
		} else if isScalarLineBreak(ch) {
			if index == 0 {
				leadingBreak = true
			}
			if index == len(rs)-1 {
				trailingBreak = true
			}
			if previousSpace {
				spaceBreak = true
			}
			previousSpace = false
			previousBreak = true
		} else {
			previousSpace = false
			previousBreak = false
		}

		index++
		precededByWhitespace = isScalarWhitespace(ch)
		followedByWhitespace = index+1 >= len(rs) || isScalarWhitespace(rs[index+1])
	}

	allowFlowPlain := true
	allowBlockPlain := true
	allowSingleQuoted := true
	allowDoubleQuoted := true
	allowBlock := true

	if leadingSpace || leadingBreak || trailingSpace || trailingBreak {
		allowFlowPlain = false
		allowBlockPlain = false
	}
	if trailingSpace {
		allowBlock = false
	}
	if breakSpace {
		allowFlowPlain = false
		allowBlockPlain = false
		allowSingleQuoted = false
	}
	if spaceBreak || specialCharacters {
		allowFlowPlain = false
		allowBlockPlain = false
		allowSingleQuoted = false
		allowBlock = false
	}
	if lineBreaks {
		allowFlowPlain = false
		allowBlockPlain = false
	}
	if flowIndicators {
		allowFlowPlain = false
	}
	if blockIndicators {
		allowBlockPlain = false
	}

	return &scalarAnalysis{
		scalar: scalar, empty: false, multiline: lineBreaks,
		allowFlowPlain: allowFlowPlain, allowBlockPlain: allowBlockPlain,
		allowSingleQuoted: allowSingleQuoted, allowDoubleQuoted: allowDoubleQuoted,
		allowBlock: allowBlock,
	}
}

// Writers.

func (e *emitter) flushStream() {}

func (e *emitter) writeStreamStart() {
	// Write BOM if needed. encoding is always None here.
}

func (e *emitter) writeStreamEnd() { e.flushStream() }

func (e *emitter) writeIndicator(indicator string, needWhitespace, whitespace, indention bool) {
	data := indicator
	if !e.whitespace && needWhitespace {
		data = " " + indicator
	}
	e.whitespace = whitespace
	e.indention = e.indention && indention
	e.column += utf8.RuneCountInString(data)
	e.openEnded = false
	e.buf.WriteString(data)
}

func (e *emitter) writeIndent() {
	indent := e.indent
	if indent < 0 {
		indent = 0
	}
	if !e.indention || e.column > indent || (e.column == indent && !e.whitespace) {
		e.writeLineBreak("")
	}
	if e.column < indent {
		e.whitespace = true
		data := strings.Repeat(" ", indent-e.column)
		e.column = indent
		e.buf.WriteString(data)
	}
}

func (e *emitter) writeLineBreak(data string) {
	if data == "" {
		data = e.bestLineBreak
	}
	e.whitespace = true
	e.indention = true
	e.line++
	e.column = 0
	e.buf.WriteString(data)
}

func (e *emitter) writeSingleQuoted(text string, split bool) {
	e.writeIndicator("'", true, false, false)
	rs := []rune(text)
	spaces := false
	breaks := false
	start, end := 0, 0
	for end <= len(rs) {
		hasCh := end < len(rs)
		var ch rune
		if hasCh {
			ch = rs[end]
		}
		if spaces {
			if !hasCh || ch != ' ' {
				if start+1 == end && e.column > e.bestWidth && split && start != 0 && end != len(rs) {
					e.writeIndent()
				} else {
					data := string(rs[start:end])
					e.column += utf8.RuneCountInString(data)
					e.buf.WriteString(data)
				}
				start = end
			}
		} else if breaks {
			if !hasCh || !isScalarLineBreak(ch) {
				if rs[start] == '\n' {
					e.writeLineBreak("")
				}
				for _, br := range rs[start:end] {
					e.writeLineBreak(string(br))
				}
				e.writeIndent()
				start = end
			}
		} else {
			if !hasCh || ch == ' ' || isScalarLineBreak(ch) || ch == '\'' {
				if start < end {
					data := string(rs[start:end])
					e.column += utf8.RuneCountInString(data)
					e.buf.WriteString(data)
					start = end
				}
			}
		}
		if ch == '\'' {
			e.column += 2
			e.buf.WriteString("''")
			start = end + 1
		}
		if hasCh {
			spaces = ch == ' '
			breaks = isScalarLineBreak(ch)
		}
		end++
	}
	e.writeIndicator("'", false, false, false)
}

var escapeReplacements = map[rune]string{
	0x00:   "0",
	0x07:   "a",
	0x08:   "b",
	0x09:   "t",
	0x0A:   "n",
	0x0B:   "v",
	0x0C:   "f",
	0x0D:   "r",
	0x1B:   "e",
	'"':    "\"",
	'\\':   "\\",
	0x85:   "N",
	0xA0:   "_",
	0x2028: "L",
	0x2029: "P",
}

func (e *emitter) writeDoubleQuoted(text string, split bool) {
	e.writeIndicator("\"", true, false, false)
	rs := []rune(text)
	start, end := 0, 0
	for end <= len(rs) {
		hasCh := end < len(rs)
		var ch rune
		if hasCh {
			ch = rs[end]
		}
		needEscape := !hasCh || ch == '"' || ch == '\\' || ch == 0x85 || ch == 0x2028 ||
			ch == 0x2029 || ch == 0xFEFF ||
			!((ch >= 0x20 && ch <= 0x7E) ||
				(e.allowUnicode && ((ch >= 0xA0 && ch <= 0xD7FF) || (ch >= 0xE000 && ch <= 0xFFFD))))
		if needEscape {
			if start < end {
				data := string(rs[start:end])
				e.column += utf8.RuneCountInString(data)
				e.buf.WriteString(data)
				start = end
			}
			if hasCh {
				var data string
				if repl, ok := escapeReplacements[ch]; ok {
					data = "\\" + repl
				} else if ch <= 0xFF {
					data = fmt.Sprintf("\\x%02X", ch)
				} else if ch <= 0xFFFF {
					data = fmt.Sprintf("\\u%04X", ch)
				} else {
					data = fmt.Sprintf("\\U%08X", ch)
				}
				e.column += len(data)
				e.buf.WriteString(data)
				start = end + 1
			}
		}
		if 0 < end && end < len(rs)-1 && ((hasCh && ch == ' ') || start >= end) &&
			e.column+(end-start) > e.bestWidth && split {
			data := "\\"
			if start < end { // Python slices text[start:end] as '' when start > end
				data = string(rs[start:end]) + "\\"
				start = end
			}
			e.column += utf8.RuneCountInString(data)
			e.buf.WriteString(data)
			e.writeIndent()
			e.whitespace = false
			e.indention = false
			if rs[start] == ' ' {
				e.column++
				e.buf.WriteString("\\")
			}
		}
		end++
	}
	e.writeIndicator("\"", false, false, false)
}

func (e *emitter) writePlain(text string, split bool) {
	if e.rootContext {
		e.openEnded = true
	}
	if text == "" {
		return
	}
	if !e.whitespace {
		e.column++
		e.buf.WriteString(" ")
	}
	e.whitespace = false
	e.indention = false
	rs := []rune(text)
	spaces := false
	breaks := false
	start, end := 0, 0
	for end <= len(rs) {
		hasCh := end < len(rs)
		var ch rune
		if hasCh {
			ch = rs[end]
		}
		if spaces {
			if !hasCh || ch != ' ' {
				if start+1 == end && e.column > e.bestWidth && split {
					e.writeIndent()
					e.whitespace = false
					e.indention = false
				} else {
					data := string(rs[start:end])
					e.column += utf8.RuneCountInString(data)
					e.buf.WriteString(data)
				}
				start = end
			}
		} else if breaks {
			if !hasCh || !isScalarLineBreak(ch) {
				if rs[start] == '\n' {
					e.writeLineBreak("")
				}
				for _, br := range rs[start:end] {
					e.writeLineBreak(string(br))
				}
				e.writeIndent()
				e.whitespace = false
				e.indention = false
				start = end
			}
		} else {
			if !hasCh || ch == ' ' || isScalarLineBreak(ch) {
				data := string(rs[start:end])
				e.column += utf8.RuneCountInString(data)
				e.buf.WriteString(data)
				start = end
			}
		}
		if hasCh {
			spaces = ch == ' '
			breaks = isScalarLineBreak(ch)
		}
		end++
	}
}
