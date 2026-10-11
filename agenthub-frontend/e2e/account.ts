import fs from 'node:fs'
import path from 'node:path'

/**
 * The shared test account is read INSIDE the test process only, from the
 * gitignored file at the repo root.
 *
 * Nothing here prints, logs, titles, attaches or screenshots a value: a password
 * in a transcript, a trace or a test title is a leak. A failure says which file
 * was unreadable or malformed and nothing more.
 */
export function readTestAccount(): { username: string; password: string } {
  const file =
    process.env.E2E_ACCOUNT_FILE ??
    path.resolve(__dirname, '..', '..', 'e2e-test-account')

  const raw = fs.readFileSync(file, 'utf8')
  const values: Record<string, string> = {}
  for (const line of raw.split('\n')) {
    const match = /^\s*(USERNAME|PASSWORD)\s*=\s*(.*)$/.exec(line)
    if (match) values[match[1]] = match[2].trim()
  }

  if (!values.USERNAME || !values.PASSWORD) {
    throw new Error(`${file} must carry USERNAME= and PASSWORD= lines; no value is logged`)
  }

  return { username: values.USERNAME, password: values.PASSWORD }
}
