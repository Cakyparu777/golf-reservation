const jpyFormatter = new Intl.NumberFormat('ja-JP', {
  style: 'currency',
  currency: 'JPY',
  maximumFractionDigits: 0,
})

export function formatJPY(amount: number) {
  return jpyFormatter.format(amount)
}
