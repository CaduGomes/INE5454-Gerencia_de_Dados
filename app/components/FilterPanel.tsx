'use client';

import { useState, useEffect, useRef } from 'react';
import { SearchFilters } from '@/lib/types';

interface FilterPanelProps {
  filters: SearchFilters;
  filterValues: {
    modelos: string[];
    tipos: string[];
    marcas: string[];
    sites: string[];
    precoMin: number;
    precoMax: number;
    espacoMin: number;
    espacoMax: number;
  };
  onFilterChange: (filters: SearchFilters) => void;
  isOpen: boolean;
  onToggle: () => void;
}

export default function FilterPanel({
  filters,
  filterValues,
  onFilterChange,
  isOpen,
  onToggle,
}: FilterPanelProps) {
  const [localFilters, setLocalFilters] = useState<SearchFilters>(filters);
  const filtersRef = useRef<string>('');

  useEffect(() => {
    const filtersKey = JSON.stringify(filters);
    // Só atualiza se realmente mudou
    if (filtersRef.current !== filtersKey) {
      filtersRef.current = filtersKey;
      setLocalFilters(filters);
    }
  }, [filters]);

  const handleFilterChange = (key: keyof SearchFilters, value: any) => {
    const newFilters = { ...localFilters, [key]: value, page: 1 };
    setLocalFilters(newFilters);
    onFilterChange(newFilters);
  };

  const handleMultiSelectChange = (key: 'modelo' | 'tipo' | 'marca' | 'site_origem', value: string) => {
    const current = localFilters[key] || [];
    const newValues = current.includes(value)
      ? current.filter((v) => v !== value)
      : [...current, value];
    handleFilterChange(key, newValues.length > 0 ? newValues : undefined);
  };

  const clearFilters = () => {
    const cleared: SearchFilters = {
      sortBy: 'preco_asc',
      page: 1,
      limit: 20,
    };
    setLocalFilters(cleared);
    onFilterChange(cleared);
  };

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
      minimumFractionDigits: 0,
    }).format(price);
  };

  const formatStorage = (gb: number) => {
    if (gb >= 1024) {
      return `${(gb / 1024).toFixed(1)} TB`;
    }
    return `${gb} GB`;
  };

  const FilterContent = () => (
    <div className="space-y-6">
      {/* Range de Preço */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Preço
        </label>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <input
              type="number"
              placeholder="Mínimo"
              value={localFilters.precoMin || ''}
              onChange={(e) =>
                handleFilterChange('precoMin', e.target.value ? parseFloat(e.target.value) : undefined)
              }
              min={filterValues.precoMin}
              max={filterValues.precoMax}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <div>
            <input
              type="number"
              placeholder="Máximo"
              value={localFilters.precoMax || ''}
              onChange={(e) =>
                handleFilterChange('precoMax', e.target.value ? parseFloat(e.target.value) : undefined)
              }
              min={filterValues.precoMin}
              max={filterValues.precoMax}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>
        <p className="text-xs text-gray-500 mt-1">
          {formatPrice(filterValues.precoMin)} - {formatPrice(filterValues.precoMax)}
        </p>
      </div>

      {/* Modelo */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Modelo
        </label>
        <div className="max-h-40 overflow-y-auto border border-gray-300 rounded-md p-2 space-y-2">
          {filterValues.modelos.map((modelo) => (
            <label key={modelo} className="flex items-center">
              <input
                type="checkbox"
                checked={localFilters.modelo?.includes(modelo) || false}
                onChange={() => handleMultiSelectChange('modelo', modelo)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <span className="ml-2 text-sm text-gray-700">{modelo}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Tipo */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Tipo
        </label>
        <div className="max-h-40 overflow-y-auto border border-gray-300 rounded-md p-2 space-y-2">
          {filterValues.tipos.map((tipo) => (
            <label key={tipo} className="flex items-center">
              <input
                type="checkbox"
                checked={localFilters.tipo?.includes(tipo) || false}
                onChange={() => handleMultiSelectChange('tipo', tipo)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <span className="ml-2 text-sm text-gray-700">{tipo}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Marca */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Marca
        </label>
        <div className="max-h-40 overflow-y-auto border border-gray-300 rounded-md p-2 space-y-2">
          {filterValues.marcas.map((marca) => (
            <label key={marca} className="flex items-center">
              <input
                type="checkbox"
                checked={localFilters.marca?.includes(marca) || false}
                onChange={() => handleMultiSelectChange('marca', marca)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <span className="ml-2 text-sm text-gray-700">{marca}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Site de Origem */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Site de Origem
        </label>
        <div className="space-y-2">
          {filterValues.sites.map((site) => (
            <label key={site} className="flex items-center">
              <input
                type="checkbox"
                checked={localFilters.site_origem?.includes(site) || false}
                onChange={() => handleMultiSelectChange('site_origem', site)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <span className="ml-2 text-sm text-gray-700">{site}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Inclui Controles */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Inclui Controles
        </label>
        <select
          value={localFilters.inclui_controles || ''}
          onChange={(e) =>
            handleFilterChange('inclui_controles', e.target.value || undefined)
          }
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="">Todos</option>
          <option value="Sim">Sim</option>
          <option value="Não">Não</option>
        </select>
      </div>

      {/* Inclui Jogos */}
      <div>
        <label className="flex items-center">
          <input
            type="checkbox"
            checked={localFilters.inclui_jogos || false}
            onChange={(e) => handleFilterChange('inclui_jogos', e.target.checked ? true : undefined)}
            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
          />
          <span className="ml-2 text-sm font-medium text-gray-700">Inclui Jogos</span>
        </label>
      </div>

      {/* Espaço em Disco */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Espaço em Disco (GB)
        </label>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <input
              type="number"
              placeholder="Mínimo"
              value={localFilters.espacoMin || ''}
              onChange={(e) =>
                handleFilterChange('espacoMin', e.target.value ? parseFloat(e.target.value) : undefined)
              }
              min={filterValues.espacoMin}
              max={filterValues.espacoMax}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <div>
            <input
              type="number"
              placeholder="Máximo"
              value={localFilters.espacoMax || ''}
              onChange={(e) =>
                handleFilterChange('espacoMax', e.target.value ? parseFloat(e.target.value) : undefined)
              }
              min={filterValues.espacoMin}
              max={filterValues.espacoMax}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>
        <p className="text-xs text-gray-500 mt-1">
          {formatStorage(filterValues.espacoMin)} - {formatStorage(filterValues.espacoMax)}
        </p>
      </div>

      {/* Ordenação */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Ordenar por
        </label>
        <select
          value={localFilters.sortBy || 'preco_asc'}
          onChange={(e) =>
            handleFilterChange('sortBy', e.target.value as 'preco_asc' | 'preco_desc')
          }
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="preco_asc">Preço: Menor para Maior</option>
          <option value="preco_desc">Preço: Maior para Menor</option>
        </select>
      </div>

      {/* Botão Limpar Filtros */}
      <button
        onClick={clearFilters}
        className="w-full px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-800 font-medium rounded-md transition-colors duration-200"
      >
        Limpar Filtros
      </button>
    </div>
  );

  return (
    <>
      {/* Botão para abrir filtros no mobile */}
      <button
        onClick={onToggle}
        className="lg:hidden fixed bottom-4 right-4 z-40 bg-blue-600 hover:bg-blue-700 text-white p-3 rounded-full shadow-lg"
      >
        <svg
          className="h-6 w-6"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"
          />
        </svg>
      </button>

      {/* Overlay no mobile */}
      {isOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black bg-opacity-50 z-30"
          onClick={onToggle}
        />
      )}

      {/* Painel de Filtros */}
      <div
        className={`
          ${isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
          fixed lg:sticky top-0 left-0 h-full lg:h-auto w-80 lg:w-full bg-white shadow-xl lg:shadow-none z-40 lg:z-auto
          transition-transform duration-300 ease-in-out
          overflow-y-auto p-6
        `}
      >
        <div className="flex items-center justify-between mb-4 lg:hidden">
          <h2 className="text-xl font-bold text-gray-900">Filtros</h2>
          <button
            onClick={onToggle}
            className="text-gray-500 hover:text-gray-700"
          >
            <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <FilterContent />
      </div>
    </>
  );
}

