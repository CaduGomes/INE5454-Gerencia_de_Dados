'use client';

import { Product } from '@/lib/types';

interface ProductCardProps {
  product: Product;
}

export default function ProductCard({ product }: ProductCardProps) {
  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
    }).format(price);
  };

  const formatStorage = (gb: number | null) => {
    if (gb === null) return 'N/A';
    if (gb >= 1024) {
      return `${(gb / 1024).toFixed(1)} TB`;
    }
    return `${gb} GB`;
  };

  return (
    <div className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow duration-200 overflow-hidden flex flex-col h-full">
      <div className="p-4 flex-1 flex flex-col">
        <h3 className="text-lg font-semibold text-gray-900 mb-2 line-clamp-2">
          {product.nome_anuncio}
        </h3>
        
        <div className="mb-3 space-y-1">
          {product.marca && (
            <p className="text-sm text-gray-600">
              <span className="font-medium">Marca:</span> {product.marca}
            </p>
          )}
          {product.modelo && (
            <p className="text-sm text-gray-600">
              <span className="font-medium">Modelo:</span> {product.modelo}
            </p>
          )}
          {product.tipo && (
            <p className="text-sm text-gray-600">
              <span className="font-medium">Tipo:</span> {product.tipo}
            </p>
          )}
        </div>

        <div className="mt-auto">
          <div className="flex items-center justify-between mb-3">
            <span className="text-2xl font-bold text-blue-600">
              {formatPrice(product.preco_vista)}
            </span>
            <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
              {product.site_origem}
            </span>
          </div>

          <div className="flex flex-wrap gap-2 mb-3">
            {product.espaco_armazenamento_gb !== null && (
              <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                {formatStorage(product.espaco_armazenamento_gb)}
              </span>
            )}
            {product.inclui_controles === 'Sim' && (
              <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">
                Inclui Controles
              </span>
            )}
            {product.inclui_jogos && (
              <span className="text-xs bg-purple-100 text-purple-800 px-2 py-1 rounded">
                Inclui Jogos
              </span>
            )}
            {product.com_leitor_disco === 'Sim' && (
              <span className="text-xs bg-orange-100 text-orange-800 px-2 py-1 rounded">
                Com Leitor de Disco
              </span>
            )}
          </div>

          <a
            href={product.link_pagina}
            target="_blank"
            rel="noopener noreferrer"
            className="block w-full text-center bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors duration-200"
          >
            Ver Produto
          </a>
        </div>
      </div>
    </div>
  );
}

