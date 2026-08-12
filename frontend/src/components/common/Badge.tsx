'use client';

import React from 'react';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'success' | 'danger' | 'warning' | 'info' | 'neutral';
  pulse?: boolean;
}

export const Badge: React.FC<BadgeProps> = ({ children, variant = 'neutral' }) => {
  let styleClasses = 'bg-[#c0c0c0] text-black border-[#404040]';

  if (variant === 'success') {
    styleClasses = 'bg-[#008000] text-white font-bold';
  } else if (variant === 'danger') {
    styleClasses = 'bg-[#cc0000] text-white font-bold';
  } else if (variant === 'warning') {
    styleClasses = 'bg-[#d97706] text-white font-bold';
  } else if (variant === 'info') {
    styleClasses = 'bg-[#000080] text-white font-bold';
  }

  return (
    <span className={`inline-block text-[11px] px-2 py-0.5 font-mono uppercase tracking-tight border border-[#404040] ${styleClasses}`}>
      {children}
    </span>
  );
};
