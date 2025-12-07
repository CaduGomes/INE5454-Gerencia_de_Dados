/**
 * Normaliza o preço de string para número
 * Lida com formatos: "3999.00", "4.499", "449.90"
 */
export function normalizePrice(priceStr: string): number {
  if (!priceStr || priceStr.trim() === '') return 0;
  
  // Remove espaços
  let cleaned = priceStr.trim().replace(/\s/g, '');
  
  // Se tem vírgula, assume que é separador decimal
  if (cleaned.includes(',')) {
    // Remove pontos (separadores de milhar) e substitui vírgula por ponto
    cleaned = cleaned.replace(/\./g, '').replace(',', '.');
  } else if (cleaned.includes('.')) {
    // Se tem ponto, verifica se é separador de milhar ou decimal
    const parts = cleaned.split('.');
    if (parts.length === 2) {
      // Se a parte após o ponto tem exatamente 2 dígitos, é decimal (ex: "449.90", "3999.00")
      if (parts[1].length === 2) {
        // Mantém como está (decimal)
      } else {
        // É separador de milhar (ex: "4.499")
        cleaned = cleaned.replace(/\./g, '');
      }
    } else {
      // Múltiplos pontos = separador de milhar
      cleaned = cleaned.replace(/\./g, '');
    }
  }
  
  const num = parseFloat(cleaned);
  return isNaN(num) ? 0 : num;
}

/**
 * Extrai o espaço em disco em GB do campo espaco_armazenamento
 * Retorna null se não conseguir extrair
 */
export function extractStorageInGB(storageStr: string): number | null {
  if (!storageStr || storageStr.trim() === '') return null;
  
  // Busca por padrões como "825 GB", "1 TB", "1TB", "825GB", etc.
  const patterns = [
    /(\d+(?:[.,]\d+)?)\s*TB/i,  // Terabytes
    /(\d+(?:[.,]\d+)?)\s*GB/i,  // Gigabytes
  ];
  
  for (const pattern of patterns) {
    const match = storageStr.match(pattern);
    if (match) {
      const value = parseFloat(match[1].replace(',', '.'));
      if (!isNaN(value)) {
        // Se for TB, converte para GB
        if (pattern.source.includes('TB')) {
          return value * 1024;
        }
        return value;
      }
    }
  }
  
  return null;
}

/**
 * Verifica se o produto inclui jogos
 * Retorna true se jogos_incluidos não estiver vazio
 */
export function hasGames(jogosIncluidos: string): boolean {
  return jogosIncluidos !== null && jogosIncluidos !== undefined && jogosIncluidos.trim() !== '';
}

