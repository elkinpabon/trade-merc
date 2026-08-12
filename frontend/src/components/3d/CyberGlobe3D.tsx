'use client';

import React, { useEffect, useRef } from 'react';

export const CyberGlobe3D: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let width = (canvas.width = canvas.parentElement?.clientWidth || 300);
    let height = (canvas.height = canvas.parentElement?.clientHeight || 200);

    // 3D Particles Sphere configuration
    const NUM_PARTICLES = 180;
    const RADIUS = Math.min(width, height) * 0.38;
    const particles: { x: number; y: number; z: number; baseSize: number }[] = [];

    for (let i = 0; i < NUM_PARTICLES; i++) {
      const phi = Math.acos(-1 + (2 * i) / NUM_PARTICLES);
      const theta = Math.sqrt(NUM_PARTICLES * Math.PI) * phi;
      particles.push({
        x: RADIUS * Math.cos(theta) * Math.sin(phi),
        y: RADIUS * Math.sin(theta) * Math.sin(phi),
        z: RADIUS * Math.cos(phi),
        baseSize: 1.5 + Math.random() * 1.5,
      });
    }

    let angleX = 0.003;
    let angleY = 0.005;

    const render = () => {
      ctx.clearRect(0, 0, width, height);

      const cx = width / 2;
      const cy = height / 2;

      // Sort by Z for depth rendering
      particles.sort((a, b) => b.z - a.z);

      ctx.save();
      ctx.translate(cx, cy);

      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];

        // 3D Rotation Math
        const cosX = Math.cos(angleX);
        const sinX = Math.sin(angleX);
        const cosY = Math.cos(angleY);
        const sinY = Math.sin(angleY);

        // Rotate Y
        let x1 = p.x * cosY - p.z * sinY;
        let z1 = p.z * cosY + p.x * sinY;

        // Rotate X
        let y1 = p.y * cosX - z1 * sinX;
        let z2 = z1 * cosX + p.y * sinX;

        p.x = x1;
        p.y = y1;
        p.z = z2;

        // Perspective Projection
        const perspective = 300 / (300 + p.z);
        const px = p.x * perspective;
        const py = p.y * perspective;
        const size = p.baseSize * perspective;

        // Depth Opacity
        const alpha = Math.max(0.1, (p.z + RADIUS) / (2 * RADIUS));

        // Connect nearby points with glowing lines
        for (let j = i + 1; j < particles.length; j++) {
          const p2 = particles[j];
          const dx = p.x - p2.x;
          const dy = p.y - p2.y;
          const dz = p.z - p2.z;
          const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);

          if (dist < 45) {
            const lineAlpha = (1 - dist / 45) * alpha * 0.35;
            ctx.beginPath();
            ctx.moveTo(px, py);
            ctx.lineTo(p2.x * perspective, p2.y * perspective);
            ctx.strokeStyle = `rgba(56, 189, 248, ${lineAlpha})`;
            ctx.lineWidth = 0.6;
            ctx.stroke();
          }
        }

        // Draw particle dot
        ctx.beginPath();
        ctx.arc(px, py, size, 0, Math.PI * 2);
        ctx.fillStyle = alpha > 0.6 ? `rgba(16, 185, 129, ${alpha})` : `rgba(56, 189, 248, ${alpha})`;
        ctx.shadowColor = alpha > 0.6 ? '#10b981' : '#38bdf8';
        ctx.shadowBlur = 6;
        ctx.fill();
      }

      ctx.restore();
      animationFrameId = requestAnimationFrame(render);
    };

    render();

    const handleResize = () => {
      if (!canvas.parentElement) return;
      width = canvas.width = canvas.parentElement.clientWidth;
      height = canvas.height = canvas.parentElement.clientHeight;
    };

    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  return <canvas ref={canvasRef} className="absolute inset-0 pointer-events-none opacity-60 z-0" />;
};
