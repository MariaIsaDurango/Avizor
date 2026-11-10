// ES: Anonimización provisional por patrones hasta que llegue el NER de Laura.
// EN: Temporary pattern-based anonymization until Laura's NER arrives.
type Entity = 'IBAN' | 'CARD' | 'ID_NUMBER' | 'EMAIL' | 'PHONE';

const RULES: [Entity, RegExp][] = [
  ['IBAN', /\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]{4}){4,7}\b/gi],
  ['CARD', /\b(?:\d[ -]?){13,19}\b/g],
  ['ID_NUMBER', /\b(?:\d{8}|[XYZ]\d{7})[ -]?[A-Z]\b/gi],
  ['EMAIL', /\b[\w.+-]+@[\w-]+\.[\w.-]+\b/g],
  ['PHONE', /(?:\+\d{2}[ ]?)?\b[6-9]\d{2}[ ]?\d{3}[ ]?\d{3}\b/g],
];

export const NER_MODEL_VERSION = 'regex-v0';

export function anonymize(text: string): { text: string; entities: Entity[] } {
  const found = new Set<Entity>();
  let result = text;
  for (const [tag, pattern] of RULES) {
    result = result.replace(pattern, () => {
      found.add(tag);
      return `[${tag}]`;
    });
  }
  return { text: result, entities: [...found] };
}

export function toE164(input: string): string | null {
  const digits = input.replace(/[\s\-().]/g, '');
  if (/^\+[1-9]\d{6,14}$/.test(digits)) return digits;
  if (/^00[1-9]\d{6,14}$/.test(digits)) return `+${digits.slice(2)}`;
  if (/^[6-9]\d{8}$/.test(digits)) return `+34${digits}`;  // ES: número español sin prefijo
  return null;
}
