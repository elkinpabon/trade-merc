import { test, expect } from '@playwright/test';

async function login(page){
  await page.goto('/');
  if(await page.getByLabel('PIN').count()){
    const pin=process.env.PULSE_E2E_PIN;
    if(!pin)throw new Error('Set PULSE_E2E_PIN only in the local Playwright environment');
    await page.getByLabel('PIN').fill(pin);
    await page.getByRole('button',{name:'Continuar'}).click();
  }
  await expect(page.getByText('Patrimonio paper',{exact:true})).toBeVisible();
}

test('unauthenticated requests blocked and invalid PIN rejected',async({page})=>{
  expect((await page.request.get('/api/overview')).status()).toBe(401);
  await page.goto('/');
  await expect(page.getByRole('heading',{name:'Iniciar sesión'})).toBeVisible();
  await page.getByLabel('PIN').fill('wrong-pin');
  await page.getByRole('button',{name:'Continuar'}).click();
  await expect(page.getByRole('alert')).toContainText('incorrectos');
  expect((await page.request.get('/api/overview')).status()).toBe(401);
});

test('real market dashboard, navigation, search and decision drawer', async ({page})=>{
  const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await login(page);
  await expect(page.getByRole('link', {name:'TRADEMERC Mercado'})).toBeVisible();
  await expect(page).toHaveTitle('TRADEMERC — Mercado');
  await page.screenshot({path:'test-results/pulse-desktop.png',fullPage:true});
  await page.getByRole('button',{name:'Escáner de mercado',exact:true}).click();
  await page.getByRole('textbox',{name:'Buscar mercado'}).fill('BTC');
  await expect(page.locator('tbody tr')).toHaveCount(1);
  await expect(page.locator('tbody')).toContainText('BTCUSDT');
  await page.getByRole('textbox',{name:'Buscar mercado'}).fill('');
  await page.getByRole('button',{name:'Analizados',exact:true}).click();
  await expect(page.locator('tbody tr').first()).toBeVisible();
  await page.locator('tbody tr').first().click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await expect(page.getByText('Precio de señal',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Cerrar detalle'}).click();
  await page.getByRole('button',{name:'Cartera paper',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Historial de operaciones'})).toBeVisible();
  await page.getByRole('button',{name:'Decisiones',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Diario de decisiones'})).toBeVisible();
  await page.getByRole('button',{name:'Estrategia',exact:true}).click();
  await expect(page.getByText('Investigación, no rentabilidad verificada',{exact:true})).toBeVisible();
  expect(errors).toEqual([]);
});

test('mobile overview fits viewport and menu opens',async({page})=>{
  await page.setViewportSize({width:390,height:844});
  await login(page);
  const widths=await page.evaluate(()=>({scroll:document.documentElement.scrollWidth,width:window.innerWidth}));
  expect(widths.scroll).toBeLessThanOrEqual(widths.width);
  await page.screenshot({path:'test-results/pulse-mobile.png',fullPage:true});
  await page.getByRole('button',{name:'Abrir menú'}).click();
  await page.getByRole('button',{name:'Estrategia',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Momentum intradía'})).toBeVisible();
});
