'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import SearchBar from '@/components/SearchBar';
import FilterPanel from '@/components/FilterPanel';
import ProductList from '@/components/ProductList';
import { Product, SearchFilters, SearchResponse } from '@/lib/types';

export default function Home() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState<SearchFilters>({
    sortBy: 'preco_asc',
    page: 1,
    limit: 20,
  });
  const [filterValues, setFilterValues] = useState<SearchResponse['filters']>({
    modelos: [],
    tipos: [],
    marcas: [],
    sites: [],
    precoMin: 0,
    precoMax: 10000,
    espacoMin: 0,
    espacoMax: 2000,
  });
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const filtersRef = useRef<string>('');

  useEffect(() => {
    // Serializa os filtros para comparar
    const filtersKey = JSON.stringify(filters);
    
    // Evita chamadas duplicadas
    if (filtersRef.current === filtersKey) {
      return;
    }
    
    filtersRef.current = filtersKey;
    
    const fetchProducts = async () => {
      setLoading(true);
      try {
        const params = new URLSearchParams();
        
        if (filters.query) params.append('query', filters.query);
        if (filters.precoMin !== undefined) params.append('precoMin', filters.precoMin.toString());
        if (filters.precoMax !== undefined) params.append('precoMax', filters.precoMax.toString());
        if (filters.modelo && filters.modelo.length > 0) params.append('modelo', filters.modelo.join(','));
        if (filters.tipo && filters.tipo.length > 0) params.append('tipo', filters.tipo.join(','));
        if (filters.marca && filters.marca.length > 0) params.append('marca', filters.marca.join(','));
        if (filters.site_origem && filters.site_origem.length > 0) params.append('site_origem', filters.site_origem.join(','));
        if (filters.inclui_controles) params.append('inclui_controles', filters.inclui_controles);
        if (filters.inclui_jogos !== undefined) params.append('inclui_jogos', filters.inclui_jogos.toString());
        if (filters.espacoMin !== undefined) params.append('espacoMin', filters.espacoMin.toString());
        if (filters.espacoMax !== undefined) params.append('espacoMax', filters.espacoMax.toString());
        if (filters.sortBy) params.append('sortBy', filters.sortBy);
        if (filters.page) params.append('page', filters.page.toString());
        if (filters.limit) params.append('limit', filters.limit.toString());

        const response = await fetch(`/api/products?${params.toString()}`);
        const data: SearchResponse = await response.json();

        setProducts(data.products);
        setTotal(data.total);
        setTotalPages(data.totalPages);
        setCurrentPage(data.page);
        setFilterValues(data.filters);
      } catch (error) {
        console.error('Erro ao buscar produtos:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchProducts();
  }, [filters]);

  const handleSearch = useCallback((query: string) => {
    setFilters((prev) => ({ ...prev, query, page: 1 }));
  }, []);

  const handleFilterChange = useCallback((newFilters: SearchFilters) => {
    setFilters(newFilters);
  }, []);

  const handlePageChange = (page: number) => {
    setFilters((prev) => ({ ...prev, page }));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <h1 className="text-2xl font-bold text-gray-900 mb-4">
            Busca de Video Games
          </h1>
          <SearchBar onSearch={handleSearch} />
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="flex flex-col lg:flex-row gap-6">
          {/* Sidebar de Filtros */}
          <aside className="lg:w-80 flex-shrink-0">
            <FilterPanel
              filters={filters}
              filterValues={filterValues}
              onFilterChange={handleFilterChange}
              isOpen={filtersOpen}
              onToggle={() => setFiltersOpen(!filtersOpen)}
            />
          </aside>

          {/* Conteúdo Principal */}
          <div className="flex-1">
            {/* Info de Resultados */}
            <div className="mb-4 flex flex-col sm:flex-row sm:items-center sm:justify-between">
              <p className="text-sm text-gray-600 mb-2 sm:mb-0">
                {loading ? (
                  'Carregando...'
                ) : (
                  <>
                    Mostrando {products.length} de {total} produtos
                  </>
                )}
              </p>
            </div>

            {/* Lista de Produtos */}
            <ProductList products={products} loading={loading} />

            {/* Paginação */}
            {totalPages > 1 && !loading && (
              <div className="mt-8 flex justify-center">
                <nav className="flex space-x-2">
                  <button
                    onClick={() => handlePageChange(currentPage - 1)}
                    disabled={currentPage === 1}
                    className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Anterior
                  </button>
                  
                  {Array.from({ length: totalPages }, (_, i) => i + 1)
                    .filter((page) => {
                      // Mostra primeira, última, atual e adjacentes
                      return (
                        page === 1 ||
                        page === totalPages ||
                        (page >= currentPage - 1 && page <= currentPage + 1)
                      );
                    })
                    .map((page, index, array) => {
                      // Adiciona ellipsis quando necessário
                      const prevPage = array[index - 1];
                      const showEllipsis = prevPage && page - prevPage > 1;
                      
                      return (
                        <div key={page} className="flex items-center">
                          {showEllipsis && (
                            <span className="px-2 text-gray-500">...</span>
                          )}
                          <button
                            onClick={() => handlePageChange(page)}
                            className={`px-4 py-2 border rounded-md text-sm font-medium ${
                              currentPage === page
                                ? 'bg-blue-600 text-white border-blue-600'
                                : 'border-gray-300 text-gray-700 bg-white hover:bg-gray-50'
                            }`}
                          >
                            {page}
                          </button>
                        </div>
                      );
                    })}

                  <button
                    onClick={() => handlePageChange(currentPage + 1)}
                    disabled={currentPage === totalPages}
                    className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Próxima
                  </button>
                </nav>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

