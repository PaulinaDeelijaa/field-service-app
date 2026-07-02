import { useEffect, useState } from "react";
import { fetchPhotoBlob } from "../services/photos";

export function AuthenticatedPhoto({
  photoId,
  alt,
  className,
}: {
  photoId: string;
  alt: string;
  className?: string;
}) {
  const [src, setSrc] = useState<string | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let objectUrl: string | null = null;
    let cancelled = false;

    fetchPhotoBlob(photoId)
      .then((url) => {
        if (cancelled) {
          URL.revokeObjectURL(url);
          return;
        }
        objectUrl = url;
        setSrc(url);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [photoId]);

  if (error) {
    return (
      <div className={`flex items-center justify-center bg-gray-100 text-xs text-gray-400 ${className ?? ""}`}>
        Unavailable
      </div>
    );
  }

  if (!src) {
    return (
      <div className={`animate-pulse bg-gray-100 ${className ?? ""}`} />
    );
  }

  return <img src={src} alt={alt} className={className} />;
}
