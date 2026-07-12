// Minimal, safe Markdown renderer (no dependencies). Handles bold, italic,
// inline code, bullet/numbered lists, headings and paragraphs. Input is
// HTML-escaped first, so it's safe to set as innerHTML.

function escapeHtml(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function inline(s) {
  return s
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/(?<!\*)\*(?!\*)([^*\n]+)\*(?!\*)/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code class="bg-black/10 rounded px-1 text-[0.85em]">$1</code>')
}

export default function Markdown({ text = '', className = '' }) {
  const lines = escapeHtml(text).split('\n')
  const out = []
  let list = null
  const flush = () => {
    if (list) { out.push(`<ul class="list-disc pl-5 space-y-1 my-1">${list.join('')}</ul>`); list = null }
  }

  for (const raw of lines) {
    const line = raw.replace(/\s+$/, '')
    const bullet = line.match(/^\s*[-•*]\s+(.*)/)
    const num = line.match(/^\s*\d+\.\s+(.*)/)
    const head = line.match(/^#{1,3}\s+(.*)/)
    if (bullet) { (list = list || []).push(`<li>${inline(bullet[1])}</li>`) }
    else if (num) { (list = list || []).push(`<li>${inline(num[1])}</li>`) }
    else if (!line.trim()) { flush(); out.push('<div class="h-1.5"></div>') }
    else if (head) { flush(); out.push(`<div class="font-bold text-[15px] mt-1 mb-0.5">${inline(head[1])}</div>`) }
    else { flush(); out.push(`<p class="leading-relaxed">${inline(line)}</p>`) }
  }
  flush()

  return <div className={className} dangerouslySetInnerHTML={{ __html: out.join('') }} />
}
