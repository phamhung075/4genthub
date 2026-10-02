package value_objects

import (
	"math"
	"math/big"
	"sync"
)

// Python's math.log / math.exp call the platform libm (glibc), whose results are
// correctly rounded in all but a vanishing fraction of cases, while Go's pure-Go
// math.Log / math.Exp are only accurate to <1 ulp and differ in the last bit for roughly
// one input in five. PyLog and PyExp compute the result with 160-bit arithmetic and round
// once, which reproduces glibc.

const mathPrec = 160

var (
	ln2Once sync.Once
	ln2Val  *big.Float
)

func bf(x float64) *big.Float { return new(big.Float).SetPrec(mathPrec).SetFloat64(x) }

func newBF() *big.Float { return new(big.Float).SetPrec(mathPrec) }

// ln2 = 2*atanh(1/3).
func ln2() *big.Float {
	ln2Once.Do(func() { ln2Val = atanh2(new(big.Float).SetPrec(mathPrec).Quo(bf(1), bf(3))) })
	return ln2Val
}

// atanh2 returns 2*atanh(z) = 2*(z + z^3/3 + z^5/5 + ...) for |z| < 1/2.
func atanh2(z *big.Float) *big.Float {
	z2 := newBF().Mul(z, z)
	term := newBF().Set(z)
	sum := newBF().Set(z)
	eps := newBF().SetMantExp(bf(1), -mathPrec-8)
	for n := int64(3); ; n += 2 {
		term.Mul(term, z2)
		t := newBF().Quo(term, newBF().SetInt64(n))
		sum.Add(sum, t)
		if newBF().Abs(t).Cmp(eps) < 0 {
			break
		}
	}
	return sum.Mul(sum, bf(2))
}

// PyLog is math.log(x) for finite x > 0; other inputs defer to math.Log (the callers
// guard the domain like Python, which raises ValueError for x <= 0).
func PyLog(x float64) float64 {
	if !(x > 0) || math.IsInf(x, 0) {
		return math.Log(x)
	}
	if x == 1 {
		return 0
	}
	m, e := math.Frexp(x) // x = m * 2^e, m in [0.5, 1)
	if m < math.Sqrt2/2 {
		m *= 2
		e--
	}
	// ln x = e*ln2 + ln m = e*ln2 + 2*atanh((m-1)/(m+1))
	mb := bf(m)
	z := newBF().Quo(newBF().Sub(mb, bf(1)), newBF().Add(mb, bf(1)))
	r := atanh2(z)
	r.Add(r, newBF().Mul(ln2(), newBF().SetInt64(int64(e))))
	f, _ := r.Float64()
	return f
}

// PyExp is math.exp(x) for finite x; overflow/underflow and non-finite inputs defer to
// math.Exp.
func PyExp(x float64) float64 {
	if math.IsNaN(x) || math.IsInf(x, 0) || x > 709 || x < -745 {
		return math.Exp(x)
	}
	if x == 0 {
		return 1
	}
	// x = k*ln2 + r, |r| <= ln2/2; exp(x) = 2^k * exp(r)
	k := math.Round(x / math.Ln2)
	r := newBF().Sub(bf(x), newBF().Mul(ln2(), bf(k)))
	// exp(r) by Taylor series after halving r 8 times, then squaring 8 times.
	const halvings = 8
	r.SetMantExp(r, -halvings)
	sum := bf(1)
	term := bf(1)
	eps := newBF().SetMantExp(bf(1), -mathPrec-8)
	for n := int64(1); ; n++ {
		term.Mul(term, r)
		term.Quo(term, newBF().SetInt64(n))
		sum.Add(sum, term)
		if newBF().Abs(term).Cmp(eps) < 0 {
			break
		}
	}
	for i := 0; i < halvings; i++ {
		sum.Mul(sum, sum)
	}
	sum.SetMantExp(sum, int(k))
	f, _ := sum.Float64()
	return f
}
