import { PolymarketView } from '@/features/polymarket/PolymarketView';

export const metadata = {
  title: 'TRADEMERC - Polymarket Prediction Engine',
  description: 'Módulo dedicado de trading cuantitativo en mercados de predicción Polymarket',
};

export default function PolymarketPage() {
  return <PolymarketView />;
}
