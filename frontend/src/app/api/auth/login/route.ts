import { NextResponse } from 'next/server';
import jwt from 'jsonwebtoken';

const JWT_SECRET = process.env.JWT_SECRET_KEY || 'trademerc-secret-jwt-key-2026';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { username, pin } = body || {};

    if (!username || !pin) {
      return NextResponse.json({ success: false, message: 'Usuario y PIN requeridos' }, { status: 400 });
    }

    // Verify authorized user credentials
    if (username.trim() === 'elkinpabon' && pin.trim() === '2002123') {
      const token = jwt.sign(
        { sub: 'elkinpabon', user_id: 'usr-1', username: 'elkinpabon' },
        JWT_SECRET,
        { expiresIn: '7d' }
      );

      return NextResponse.json({
        success: true,
        token,
        user: { id: 'usr-1', username: 'elkinpabon', is_admin: true },
        message: 'Autenticación exitosa en TRADEMERC'
      }, { status: 200 });
    }

    return NextResponse.json({ success: false, message: 'Usuario o PIN incorrectos' }, { status: 401 });
  } catch (error: any) {
    return NextResponse.json({ success: false, message: error?.message || 'Error en el servidor' }, { status: 500 });
  }
}
