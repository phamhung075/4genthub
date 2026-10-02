package pyyaml

// Serializer (serializer.py): walks the node tree and turns it into events. Anchors and
// the path resolver are inert here (a JSON-decoded tree has neither shared nodes nor
// path resolvers), so anchor_node assigns no anchors and serialized_nodes never repeats.

type serializer struct {
	em  *emitter
	res *resolver
}

func newSerializer(em *emitter) *serializer {
	return &serializer{em: em, res: defaultResolver}
}

func (s *serializer) serialize(n node) {
	s.em.emit(documentStartEvent{})
	s.serializeNode(n)
	s.em.emit(documentEndEvent{})
}

func (s *serializer) serializeNode(n node) {
	switch v := n.(type) {
	case *scalarNode:
		detectedTag := s.res.resolveScalar(v.value, true)
		defaultTag := s.res.resolveScalar(v.value, false)
		implicit := [2]bool{v.tag == detectedTag, v.tag == defaultTag}
		s.em.emit(scalarEvent{tag: v.tag, implicit: implicit, value: v.value, style: v.style})
	case *sequenceNode:
		implicit := v.tag == defaultSequenceTag
		s.em.emit(sequenceStartEvent{tag: v.tag, implicit: implicit, flowStyle: false})
		for _, item := range v.value {
			s.serializeNode(item)
		}
		s.em.emit(sequenceEndEvent{})
	case *mappingNode:
		implicit := v.tag == defaultMappingTag
		s.em.emit(mappingStartEvent{tag: v.tag, implicit: implicit, flowStyle: false})
		for _, pair := range v.value {
			s.serializeNode(pair.key)
			s.serializeNode(pair.value)
		}
		s.em.emit(mappingEndEvent{})
	}
}
