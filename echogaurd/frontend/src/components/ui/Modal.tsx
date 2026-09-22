import React, { useEffect } from 'react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  className?: string;
}

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  children,
  className = '',
}) => {
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleBackdropClick = (event: React.MouseEvent<HTMLDivElement>) => {
    if (event.target === event.currentTarget) onClose();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby={title ? 'modal-title' : undefined}
      onClick={handleBackdropClick}
    >
      <div
        className={`relative w-full max-w-lg rounded-xl border border-[var(--color-muted)] bg-[var(--color-bg-surface)] p-6 shadow-2xl ${className}`}
      >
        <button
          type="button"
          onClick={onClose}
          className="absolute right-3 top-3 rounded-md px-2 py-1 text-slate-400 hover:bg-slate-800 hover:text-white"
          aria-label="Close modal"
        >
          X
        </button>
        {title && (
          <h2
            id="modal-title"
            className="mb-4 pr-8 text-xl font-semibold text-white"
          >
            {title}
          </h2>
        )}
        <div>{children}</div>
      </div>
    </div>
  );
};

export default Modal;
