package entities

import (
	"bytes"
	"encoding/json"
	"errors"
	"io"
	"math/big"
	"strconv"
)

// DecodeJSON is json.loads: objects become *OrderedMap[any] in document order (a repeated
// key keeps its first position and takes the last value, like a dict), arrays []any,
// integers int64 (*big.Int beyond that), other numbers float64. The NaN / Infinity
// literals are rejected (accepted deviation).
func DecodeJSON(data []byte) (any, error) {
	dec := json.NewDecoder(bytes.NewReader(data))
	dec.UseNumber()
	v, err := decodeJSONValue(dec)
	if err != nil {
		return nil, err
	}
	if _, err := dec.Token(); err != io.EOF {
		return nil, errors.New("Extra data")
	}
	return v, nil
}

func decodeJSONValue(dec *json.Decoder) (any, error) {
	tok, err := dec.Token()
	if err != nil {
		return nil, err
	}
	switch t := tok.(type) {
	case json.Delim:
		if t == '{' {
			om := NewOrderedMap[any]()
			for dec.More() {
				k, err := dec.Token()
				if err != nil {
					return nil, err
				}
				v, err := decodeJSONValue(dec)
				if err != nil {
					return nil, err
				}
				om.Set(k.(string), v)
			}
			_, err := dec.Token()
			return om, err
		}
		list := []any{}
		for dec.More() {
			v, err := decodeJSONValue(dec)
			if err != nil {
				return nil, err
			}
			list = append(list, v)
		}
		_, err := dec.Token()
		return list, err
	case json.Number:
		if i, err := strconv.ParseInt(string(t), 10, 64); err == nil {
			return i, nil
		}
		if b, ok := new(big.Int).SetString(string(t), 10); ok {
			return b, nil
		}
		f, _ := strconv.ParseFloat(string(t), 64)
		return f, nil
	}
	return tok, nil
}
