/**
 * Tipo para produto raw do JSON
 */
export interface RawProduct {
  preco_vista: string;
  preco_parcelado: string;
  modelo: string;
  nome_anuncio: string;
  link_pagina: string;
  tipo: string;
  console_type: string;
  cor: string;
  com_leitor_disco: string;
  espaco_armazenamento: string;
  jogos_incluidos: string;
  inclui_controles: string;
  marca: string;
  site_origem: string;
  data_coleta: string;
  disponibilidade: string;
}

/**
 * Tipo para produto normalizado
 */
export interface Product {
  preco_vista: number;
  preco_parcelado: string;
  modelo: string;
  nome_anuncio: string;
  link_pagina: string;
  tipo: string;
  console_type: string;
  cor: string;
  com_leitor_disco: string;
  espaco_armazenamento: string;
  espaco_armazenamento_gb: number | null;
  jogos_incluidos: string;
  inclui_jogos: boolean;
  inclui_controles: string;
  marca: string;
  site_origem: string;
  data_coleta: string;
  disponibilidade: string;
}

/**
 * Tipo para filtros de busca
 */
export interface SearchFilters {
  query?: string;
  precoMin?: number;
  precoMax?: number;
  modelo?: string[];
  tipo?: string[];
  marca?: string[];
  site_origem?: string[];
  inclui_controles?: string;
  inclui_jogos?: boolean;
  espacoMin?: number;
  espacoMax?: number;
  sortBy?: 'preco_asc' | 'preco_desc';
  page?: number;
  limit?: number;
}

/**
 * Tipo para resposta da API
 */
export interface SearchResponse {
  products: Product[];
  total: number;
  page: number;
  limit: number;
  totalPages: number;
  filters: {
    modelos: string[];
    tipos: string[];
    marcas: string[];
    sites: string[];
    precoMin: number;
    precoMax: number;
    espacoMin: number;
    espacoMax: number;
  };
}

