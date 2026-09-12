import { useCallback, useEffect, useRef } from 'react';
import createGlobe from 'cobe';

const defaultMarkers = [];

export function GlobeAnalytics({ markers = defaultMarkers, className = '', speed = 0.003 }) {
  const canvasRef = useRef(null);
  const pointerInteracting = useRef(null);
  const dragOffset = useRef({ phi: 0, theta: 0 });
  const phiOffsetRef = useRef(0);
  const thetaOffsetRef = useRef(0);
  const isPausedRef = useRef(false);

  const handlePointerDown = useCallback((e) => {
    pointerInteracting.current = { x: e.clientX, y: e.clientY };
    if (canvasRef.current) {
      canvasRef.current.style.cursor = 'grabbing';
    }
    isPausedRef.current = true;
  }, []);

  const handlePointerUp = useCallback(() => {
    if (pointerInteracting.current !== null) {
      phiOffsetRef.current += dragOffset.current.phi;
      thetaOffsetRef.current += dragOffset.current.theta;
      dragOffset.current = { phi: 0, theta: 0 };
    }
    pointerInteracting.current = null;
    if (canvasRef.current) {
      canvasRef.current.style.cursor = 'grab';
    }
    isPausedRef.current = false;
  }, []);

  useEffect(() => {
    const handlePointerMove = (e) => {
      if (pointerInteracting.current !== null) {
        dragOffset.current = {
          phi: (e.clientX - pointerInteracting.current.x) / 300,
          theta: (e.clientY - pointerInteracting.current.y) / 1000,
        };
      }
    };

    window.addEventListener('pointermove', handlePointerMove, { passive: true });
    window.addEventListener('pointerup', handlePointerUp, { passive: true });

    return () => {
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerup', handlePointerUp);
    };
  }, [handlePointerUp]);

  useEffect(() => {
    if (!canvasRef.current) {
      return undefined;
    }

    const canvas = canvasRef.current;
    let globe = null;
    let phi = 0;
    let ro;

    const init = () => {
      const width = canvas.offsetWidth;
      if (width === 0 || globe) {
        return;
      }

      globe = createGlobe(canvas, {
        devicePixelRatio: Math.min(window.devicePixelRatio || 1, 2),
        width,
        height: width,
        phi: 0,
        theta: 0.18,
        dark: 0,
        diffuse: 1.35,
        mapSamples: 22000,
        mapBrightness: 2.2,
        baseColor: [0.93, 0.88, 0.77],
        markerColor: [0.18, 0.16, 0.12],
        glowColor: [0.86, 0.79, 0.66],
        markerElevation: 0,
        markers: markers.map((m) => ({ location: m.location, size: m.size })),
        arcs: [],
        onRender: (state) => {
          if (!isPausedRef.current) {
            phi += speed;
          }
          state.phi = phi + phiOffsetRef.current + dragOffset.current.phi;
          state.theta = 0.2 + thetaOffsetRef.current + dragOffset.current.theta;
        },
      });

      setTimeout(() => {
        if (canvas) {
          canvas.style.opacity = '0.9';
        }
      }, 60);
    };

    if (canvas.offsetWidth > 0) {
      init();
    } else {
      ro = new ResizeObserver((entries) => {
        if (entries[0]?.contentRect.width > 0) {
          ro.disconnect();
          init();
        }
      });
      ro.observe(canvas);
    }

    return () => {
      if (ro) {
        ro.disconnect();
      }
      if (globe) {
        globe.destroy();
      }
    };
  }, [markers, speed]);

  return (
    <div className={`globe-wrap ${className}`.trim()}>
      <canvas
        ref={canvasRef}
        onPointerDown={handlePointerDown}
        className="globe-canvas"
        aria-label="Interactive global activity map"
      />
    </div>
  );
}
