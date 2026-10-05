package pyyaml

// Representation graph nodes (nodes.py): ScalarNode / SequenceNode / MappingNode.
// start_mark / end_mark are always None in the dumper pipeline, so they are omitted.

type node interface{ isNode() }

type scalarNode struct {
	tag   string
	value string
	style string // "" mirrors Python style=None
}

func (*scalarNode) isNode() {}

type nodePair struct {
	key   node
	value node
}

type sequenceNode struct {
	tag   string
	value []node
}

func (*sequenceNode) isNode() {}

type mappingNode struct {
	tag   string
	value []nodePair
}

func (*mappingNode) isNode() {}
