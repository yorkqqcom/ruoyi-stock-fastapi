import FileSaver from 'file-saver'
import XLSX from 'xlsx'

export function exportJsonToExcel(options) {
  const { header = [], data = [], filename = 'excel' } = options
  const ws = XLSX.utils.aoa_to_sheet([header, ...data])
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, 'Sheet1')
  const wbout = XLSX.write(wb, { bookType: 'xlsx', type: 'array' })
  const blob = new Blob([wbout], { type: 'application/octet-stream' })
  FileSaver.saveAs(blob, `${filename}.xlsx`)
}
