import { useRef, useState } from 'react'

const ACCEPTED = '.pdf,.jpg,.jpeg,.png,.mp4'
const MAX_MB = 50
const MAX_BYTES = MAX_MB * 1024 * 1024

interface Props {
  onUpload: (file: File) => Promise<void>
}

export function EvidenciaUploader({ onUpload }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')

  async function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setError('')

    if (file.size > MAX_BYTES) {
      setError(`El archivo supera el límite de ${MAX_MB} MB.`)
      return
    }

    setUploading(true)
    try {
      await onUpload(file)
    } catch (err: unknown) {
      const e2 = err as { data?: { archivo?: string; detail?: string }; message?: string }
      setError(e2?.data?.archivo ?? e2?.data?.detail ?? e2?.message ?? 'Error al subir el archivo.')
    } finally {
      setUploading(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  return (
    <div>
      <button
        type="button"
        disabled={uploading}
        onClick={() => inputRef.current?.click()}
        className="text-sm text-blue-600 hover:underline disabled:opacity-50"
      >
        {uploading ? 'Subiendo...' : '+ Agregar evidencia'}
      </button>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED}
        className="hidden"
        onChange={handleChange}
      />
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
    </div>
  )
}
