import React from 'react';

interface AvatarProps extends React.HTMLAttributes<HTMLDivElement> {
  src?: string;
  alt?: string;
  size?: number;
  fallback?: string;
  className?: string;
}

/** Avatar component – circular image with optional initials fallback */
export const Avatar: React.FC<AvatarProps> = ({
  src,
  alt = 'Avatar',
  size = 40,
  fallback = '',
  className = '',
  ...rest
}) => {
  const [hasError, setHasError] = React.useState(false);
  const dimension = size + 'px';
  const baseClass = `inline-flex items-center justify-center rounded-full overflow-hidden bg-[var(--color-muted)] ${className}`;

  return (
    <div className={baseClass} style={{ width: dimension, height: dimension }} {...rest}>
      {src && !hasError ? (
        <img src={src} alt={alt} className="object-cover w-full h-full" onError={() => setHasError(true)} />
      ) : (
        <span className="text-sm font-medium text-white">{fallback}</span>
      )}
    </div>
  );
};
