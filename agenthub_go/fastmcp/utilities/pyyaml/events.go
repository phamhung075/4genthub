package pyyaml

// Events (events.py). The default dumper never sets anchors, explicit document markers,
// versions or tags, but the fields the emitter reads are kept.

type event interface{ isEvent() }

type streamStartEvent struct{}

func (streamStartEvent) isEvent() {}

type streamEndEvent struct{}

func (streamEndEvent) isEvent() {}

type documentStartEvent struct{}

func (documentStartEvent) isEvent() {}

type documentEndEvent struct{}

func (documentEndEvent) isEvent() {}

type aliasEvent struct {
	anchor string
}

func (aliasEvent) isEvent() {}

type scalarEvent struct {
	anchor   string
	tag      string
	implicit [2]bool
	value    string
	style    string // "" mirrors Python style=None
}

func (scalarEvent) isEvent() {}

type sequenceStartEvent struct {
	anchor    string
	tag       string
	implicit  bool
	flowStyle bool
}

func (sequenceStartEvent) isEvent() {}

type sequenceEndEvent struct{}

func (sequenceEndEvent) isEvent() {}

type mappingStartEvent struct {
	anchor    string
	tag       string
	implicit  bool
	flowStyle bool
}

func (mappingStartEvent) isEvent() {}

type mappingEndEvent struct{}

func (mappingEndEvent) isEvent() {}
