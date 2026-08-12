import mysql from 'mysql2/promise';

let pool: mysql.Pool | null = null;

export function getDbPool() {
  if (!pool) {
    pool = mysql.createPool({
      host: process.env.DB_HOST || 'gateway01.us-east-1.prod.aws.tidbcloud.com',
      port: Number(process.env.DB_PORT || 4000),
      user: process.env.DB_USER || '3RWNAdLev5dv3er.root',
      password: process.env.DB_PASSWORD || 'VSGF3kkVfo4CEIu9',
      database: process.env.DB_NAME || 'trademerc_db',
      ssl: {
        rejectUnauthorized: false
      },
      waitForConnections: true,
      connectionLimit: 5,
      queueLimit: 0
    });
  }
  return pool;
}
