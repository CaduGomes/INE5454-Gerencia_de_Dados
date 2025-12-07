import { NextRequest, NextResponse } from 'next/server';
import { loadProducts, getFilterValues } from '@/lib/data-loader';
import { Product, SearchFilters, SearchResponse } from '@/lib/types';

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    
    // Parse filtros da query string
    const filters: SearchFilters = {
      query: searchParams.get('query') || undefined,
      precoMin: searchParams.get('precoMin') ? parseFloat(searchParams.get('precoMin')!) : undefined,
      precoMax: searchParams.get('precoMax') ? parseFloat(searchParams.get('precoMax')!) : undefined,
      modelo: searchParams.get('modelo') ? searchParams.get('modelo')!.split(',') : undefined,
      tipo: searchParams.get('tipo') ? searchParams.get('tipo')!.split(',') : undefined,
      marca: searchParams.get('marca') ? searchParams.get('marca')!.split(',') : undefined,
      site_origem: searchParams.get('site_origem') ? searchParams.get('site_origem')!.split(',') : undefined,
      inclui_controles: searchParams.get('inclui_controles') || undefined,
      inclui_jogos: searchParams.get('inclui_jogos') === 'true' ? true : undefined,
      espacoMin: searchParams.get('espacoMin') ? parseFloat(searchParams.get('espacoMin')!) : undefined,
      espacoMax: searchParams.get('espacoMax') ? parseFloat(searchParams.get('espacoMax')!) : undefined,
      sortBy: (searchParams.get('sortBy') as 'original' | 'preco_asc' | 'preco_desc') || 'original',
      page: searchParams.get('page') ? parseInt(searchParams.get('page')!) : 1,
      limit: searchParams.get('limit') ? parseInt(searchParams.get('limit')!) : 20,
    };

    // Carrega todos os produtos
    let products = loadProducts();

    // Aplica busca por texto
    if (filters.query) {
      const queryLower = filters.query.toLowerCase();
      products = products.filter((product) => {
        const searchableText = [
          product.nome_anuncio,
          product.modelo,
          product.tipo,
          product.marca,
          product.cor,
        ]
          .filter(Boolean)
          .join(' ')
          .toLowerCase();
        return searchableText.includes(queryLower);
      });
    }

    // Aplica filtros
    if (filters.precoMin !== undefined) {
      products = products.filter((p) => p.preco_vista >= filters.precoMin!);
    }
    if (filters.precoMax !== undefined) {
      products = products.filter((p) => p.preco_vista <= filters.precoMax!);
    }
    if (filters.modelo && filters.modelo.length > 0) {
      products = products.filter((p) => filters.modelo!.includes(p.modelo));
    }
    if (filters.tipo && filters.tipo.length > 0) {
      products = products.filter((p) => filters.tipo!.includes(p.tipo));
    }
    if (filters.marca && filters.marca.length > 0) {
      products = products.filter((p) => filters.marca!.includes(p.marca));
    }
    if (filters.site_origem && filters.site_origem.length > 0) {
      products = products.filter((p) => filters.site_origem!.includes(p.site_origem));
    }
    if (filters.inclui_controles !== undefined) {
      products = products.filter((p) => p.inclui_controles === filters.inclui_controles);
    }
    if (filters.inclui_jogos !== undefined) {
      products = products.filter((p) => p.inclui_jogos === filters.inclui_jogos);
    }
    if (filters.espacoMin !== undefined) {
      products = products.filter((p) => 
        p.espaco_armazenamento_gb !== null && p.espaco_armazenamento_gb >= filters.espacoMin!
      );
    }
    if (filters.espacoMax !== undefined) {
      products = products.filter((p) => 
        p.espaco_armazenamento_gb !== null && p.espaco_armazenamento_gb <= filters.espacoMax!
      );
    }

    // Ordenação
    if (filters.sortBy === 'preco_asc') {
      products.sort((a, b) => a.preco_vista - b.preco_vista);
    } else if (filters.sortBy === 'preco_desc') {
      products.sort((a, b) => b.preco_vista - a.preco_vista);
    } else if (filters.sortBy === 'original' || !filters.sortBy) {
      products.sort((a, b) => a.originalIndex - b.originalIndex);
    }

    // Paginação
    const total = products.length;
    const page = filters.page || 1;
    const limit = filters.limit || 20;
    const startIndex = (page - 1) * limit;
    const endIndex = startIndex + limit;
    const paginatedProducts = products.slice(startIndex, endIndex);

    // Obtém valores de filtros disponíveis (baseado em todos os produtos originais)
    const allProducts = loadProducts();
    const filterValues = getFilterValues(allProducts);

    const response: SearchResponse = {
      products: paginatedProducts,
      total,
      page,
      limit,
      totalPages: Math.ceil(total / limit),
      filters: filterValues,
    };

    return NextResponse.json(response);
  } catch (error) {
    console.error('Erro na API de produtos:', error);
    return NextResponse.json(
      { error: 'Erro ao buscar produtos' },
      { status: 500 }
    );
  }
}

