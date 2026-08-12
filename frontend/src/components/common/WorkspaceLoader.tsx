'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Terminal, Shield } from 'lucide-react';

interface WorkspaceLoaderProps {
  targetPath: string;
  targetName: string;
  targetDesc: string;
  onComplete?: () => void;
}

export const WorkspaceLoader: React.FC<WorkspaceLoaderProps> = ({
  targetPath,
  targetName,
  targetDesc
}) => {
  const [progress, setProgress] = useState(0);
  const [statusText, setStatusText] = useState('Inicializando sistema...');
  const router = useRouter();

  useEffect(() => {
    const steps = [
      { p: 15, text: 'Cargando protocolo de seguridad y autenticación...' },
      { p: 35, text: 'Conectando a base de datos de datos de mercado...' },
      { p: 65, text: `Cargando entorno táctico: ${targetName}...` },
      { p: 85, text: 'Verificando modelos de inteligencia artificial y parámetros...' },
      { p: 100, text: '¡Entorno listo! Redirigiendo...' }
    ];

    let currentStep = 0;
    const interval = setInterval(() => {
      if (currentStep < steps.length) {
        setProgress(steps[currentStep].p);
        setStatusText(steps[currentStep].text);
        currentStep++;
      } else {
        clearInterval(interval);
        setTimeout(() => {
          router.push(targetPath);
        }, 300);
      }
    }, 400);

    return () => clearInterval(interval);
  }, [targetPath, targetName, router]);

  return (
    <div className="fixed inset-0 bg-[#008080] z-50 flex items-center justify-center p-4 font-sans text-black">
      <div className="win95-window w-full max-w-md p-2 shadow-2xl">
        <div className="win95-titlebar mb-3">
          <div className="flex items-center gap-2">
            <Shield className="h-4 w-4 text-white" />
            <span>Cargando Módulo TRADEMERC</span>
          </div>
          <span className="font-mono text-xs text-white">SYSTEM_INIT</span>
        </div>

        <div className="win95-panel p-4 space-y-4 bg-[#c0c0c0]">
          <div className="win95-inset bg-white p-3 text-center space-y-1 font-mono">
            <div className="font-bold text-sm text-[#000080]">{targetName}</div>
            <div className="text-xs text-[#808080]">{targetDesc}</div>
          </div>

          <div className="space-y-2">
            <div className="flex justify-between text-xs font-mono font-bold">
              <span className="text-[#000080]">{statusText}</span>
              <span className="text-black">{progress}%</span>
            </div>

            {/* Win95 Progress Bar */}
            <div className="w-full bg-white h-5 win95-inset p-0.5 flex overflow-hidden">
              <div
                className="bg-[#000080] h-full transition-all duration-300 flex items-center justify-end pr-1 text-[10px] text-white font-mono font-bold"
                style={{ width: `${progress}%` }}
              >
                {progress > 10 && `${progress}%`}
              </div>
            </div>
          </div>

          <div className="win95-inset bg-black p-2 font-mono text-[11px] text-[#00ff00] h-20 overflow-y-auto space-y-0.5">
            <div>[SYS_BOOT] Verificando integridad de memoria... OK</div>
            <div>[NET_INIT] Estableciendo conexión segura TiDB Cloud... OK</div>
            {progress >= 35 && <div>[API_SYNC] Sincronizando feeds de datos de mercado... OK</div>}
            {progress >= 65 && <div>[WORKSP_LOAD] Entorno táctico configurado... OK</div>}
            {progress >= 85 && <div>[READY] Redirigiendo a workspace seleccionado...</div>}
          </div>
        </div>
      </div>
    </div>
  );
};
