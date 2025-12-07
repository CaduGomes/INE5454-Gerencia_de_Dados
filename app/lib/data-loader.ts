import { RawProduct, Product } from './types';
import { normalizePrice, extractStorageInGB, hasGames } from './utils';
import fs from 'fs';
import path from 'path';

let cachedProducts: Product[] | null = null;

/**
 * Carrega e combina os dados dos dois JSONs
 */
export function loadProducts(): Product[] {
  if (cachedProducts) {
    return cachedProducts;
  }

  try {
    const magazineluizaPath = path.join(process.cwd(), "..", 'magazineluiza_products.json');
    const mercadolivrePath = path.join(process.cwd(), "..", 'mercadolivre_products.json');

    const magazineluizaData: RawProduct[] = JSON.parse(
      fs.readFileSync(magazineluizaPath, 'utf-8')
    );
    const mercadolivreData: RawProduct[] = JSON.parse(
      fs.readFileSync(mercadolivrePath, 'utf-8')
    );

    const allRawProducts = [...magazineluizaData, ...mercadolivreData];

    // Normaliza os produtos
    const normalizedProducts: Product[] = allRawProducts.map((raw) => ({
      ...raw,
      preco_vista: normalizePrice(raw.preco_vista),
      espaco_armazenamento_gb: extractStorageInGB(raw.espaco_armazenamento),
      inclui_jogos: hasGames(raw.jogos_incluidos),
    }));

    cachedProducts = normalizedProducts;
    return normalizedProducts;
  } catch (error) {
    console.error('Erro ao carregar produtos:', error);
    return [];
  }
}

/**
 * Obtém valores únicos para filtros
 */
export function getFilterValues(products: Product[]) {
  const modelos = new Set<string>();
  const tipos = new Set<string>();
  const marcas = new Set<string>();
  const sites = new Set<string>();
  let precoMin = Infinity;
  let precoMax = 0;
  let espacoMin = Infinity;
  let espacoMax = 0;

  products.forEach((product) => {
    if (product.modelo && product.modelo.trim()) {
      modelos.add(product.modelo);
    }
    if (product.tipo && product.tipo.trim()) {
      tipos.add(product.tipo);
    }
    if (product.marca && product.marca.trim()) {
      marcas.add(product.marca);
    }
    if (product.site_origem && product.site_origem.trim()) {
      sites.add(product.site_origem);
    }
    
    if (product.preco_vista > 0) {
      precoMin = Math.min(precoMin, product.preco_vista);
      precoMax = Math.max(precoMax, product.preco_vista);
    }
    
    if (product.espaco_armazenamento_gb !== null) {
      espacoMin = Math.min(espacoMin, product.espaco_armazenamento_gb);
      espacoMax = Math.max(espacoMax, product.espaco_armazenamento_gb);
    }
  });

  return {
    modelos: Array.from(modelos).sort(),
    tipos: Array.from(tipos).sort(),
    marcas: Array.from(marcas).sort(),
    sites: Array.from(sites).sort(),
    precoMin: precoMin === Infinity ? 0 : Math.floor(precoMin),
    precoMax: precoMax === 0 ? 10000 : Math.ceil(precoMax),
    espacoMin: espacoMin === Infinity ? 0 : Math.floor(espacoMin),
    espacoMax: espacoMax === 0 ? 2000 : Math.ceil(espacoMax),
  };
}

