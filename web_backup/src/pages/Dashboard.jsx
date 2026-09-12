import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { gsap } from 'gsap';
import { useUser } from '../contexts/UserContext';
import { FEATURE_VISIBILITY } from '../config/featureVisibility';
import { getRoleCapabilities, getPermissionReason } from '../utils/rolePermissions';
import './Dashboard.css';

class Vector2D {
  constructor(x, y) {
    this.x = x;
    this.y = y;
  }

  static random(randomFn, min, max) {
    return min + randomFn() * (max - min);
  }
}

class Vector3D {
  constructor(x, y, z) {
    this.x = x;
    this.y = y;
    this.z = z;
  }
}

class Star {
  constructor(randomFn, cameraZ, cameraTravelDistance) {
    this.angle = randomFn() * Math.PI * 2;
    this.distance = 30 * randomFn() + 15;
    this.rotationDirection = randomFn() > 0.5 ? 1 : -1;
    this.expansionRate = 1.2 + randomFn() * 0.8;
    this.finalScale = 0.7 + randomFn() * 0.6;

    this.dx = this.distance * Math.cos(this.angle);
    this.dy = this.distance * Math.sin(this.angle);

    this.spiralLocation = (1 - Math.pow(1 - randomFn(), 3.0)) / 1.3;
    this.z = Vector2D.random(randomFn, 0.5 * cameraZ, cameraTravelDistance + cameraZ);

    const lerp = (start, end, t) => start * (1 - t) + end * t;
    this.z = lerp(this.z, cameraTravelDistance / 2, 0.3 * this.spiralLocation);
    this.strokeWeightFactor = Math.pow(randomFn(), 2.0);
  }

  render(progress, controller) {
    const spiralPos = controller.spiralPath(this.spiralLocation);
    const q = progress - this.spiralLocation;
    if (q <= 0) {
      return;
    }

    const displacementProgress = controller.constrain(4 * q, 0, 1);
    const linearEasing = displacementProgress;
    const elasticEasing = controller.easeOutElastic(displacementProgress);
    const powerEasing = Math.pow(displacementProgress, 2);

    let easing = powerEasing;
    if (displacementProgress < 0.3) {
      easing = controller.lerp(linearEasing, powerEasing, displacementProgress / 0.3);
    } else if (displacementProgress < 0.7) {
      const t = (displacementProgress - 0.3) / 0.4;
      easing = controller.lerp(powerEasing, elasticEasing, t);
    } else {
      easing = elasticEasing;
    }

    let screenX = spiralPos.x;
    let screenY = spiralPos.y;

    if (displacementProgress < 0.3) {
      screenX = controller.lerp(spiralPos.x, spiralPos.x + this.dx * 0.3, easing / 0.3);
      screenY = controller.lerp(spiralPos.y, spiralPos.y + this.dy * 0.3, easing / 0.3);
    } else if (displacementProgress < 0.7) {
      const midProgress = (displacementProgress - 0.3) / 0.4;
      const curveStrength = Math.sin(midProgress * Math.PI) * this.rotationDirection * 1.5;

      const baseX = spiralPos.x + this.dx * 0.3;
      const baseY = spiralPos.y + this.dy * 0.3;
      const targetX = spiralPos.x + this.dx * 0.7;
      const targetY = spiralPos.y + this.dy * 0.7;
      const perpX = -this.dy * 0.4 * curveStrength;
      const perpY = this.dx * 0.4 * curveStrength;

      screenX = controller.lerp(baseX, targetX, midProgress) + perpX * midProgress;
      screenY = controller.lerp(baseY, targetY, midProgress) + perpY * midProgress;
    } else {
      const finalProgress = (displacementProgress - 0.7) / 0.3;
      const baseX = spiralPos.x + this.dx * 0.7;
      const baseY = spiralPos.y + this.dy * 0.7;

      const targetDistance = this.distance * this.expansionRate * 1.5;
      const spiralTurns = 1.2 * this.rotationDirection;
      const spiralAngle = this.angle + spiralTurns * finalProgress * Math.PI;

      const targetX = spiralPos.x + targetDistance * Math.cos(spiralAngle);
      const targetY = spiralPos.y + targetDistance * Math.sin(spiralAngle);

      screenX = controller.lerp(baseX, targetX, finalProgress);
      screenY = controller.lerp(baseY, targetY, finalProgress);
    }

    const vx = ((this.z - controller.cameraZ) * screenX) / controller.viewZoom;
    const vy = ((this.z - controller.cameraZ) * screenY) / controller.viewZoom;

    const position = new Vector3D(vx, vy, this.z);

    let sizeMultiplier = 1;
    if (displacementProgress < 0.6) {
      sizeMultiplier = 1 + displacementProgress * 0.2;
    } else {
      const t = (displacementProgress - 0.6) / 0.4;
      sizeMultiplier = 1.2 * (1 - t) + this.finalScale * t;
    }

    const dotSize = 8.5 * this.strokeWeightFactor * sizeMultiplier;
    controller.showProjectedDot(position, dotSize);
  }
}

class AnimationController {
  constructor(ctx, width, height) {
    this.ctx = ctx;
    this.width = width;
    this.height = height;
    this.time = 0;
    this.stars = [];

    this.changeEventTime = 0.32;
    this.cameraZ = -400;
    this.cameraTravelDistance = 3400;
    this.startDotYOffset = 28;
    this.viewZoom = 100;
    this.numberOfStars = 5000;
    this.trailLength = 80;

    this.timeline = gsap.timeline({ repeat: -1 });
    this.populateStarsWithSeed(1234);
    this.setupTimeline();
  }

  createSeededRandom(seed) {
    let current = seed;
    return () => {
      current = (current * 9301 + 49297) % 233280;
      return current / 233280;
    };
  }

  populateStarsWithSeed(seed) {
    const randomFn = this.createSeededRandom(seed);
    this.stars = [];
    for (let i = 0; i < this.numberOfStars; i += 1) {
      this.stars.push(new Star(randomFn, this.cameraZ, this.cameraTravelDistance));
    }
  }

  setupTimeline() {
    this.timeline.to(this, {
      time: 1,
      duration: 15,
      repeat: -1,
      ease: 'none',
      onUpdate: () => this.render(),
    });
  }

  constrain(value, min, max) {
    return Math.min(Math.max(value, min), max);
  }

  map(value, start1, stop1, start2, stop2) {
    return start2 + (stop2 - start2) * ((value - start1) / (stop1 - start1));
  }

  lerp(start, end, t) {
    return start * (1 - t) + end * t;
  }

  ease(p, g) {
    if (p < 0.5) {
      return 0.5 * Math.pow(2 * p, g);
    }
    return 1 - 0.5 * Math.pow(2 * (1 - p), g);
  }

  easeOutElastic(x) {
    const c4 = (2 * Math.PI) / 4.5;
    if (x <= 0) {
      return 0;
    }
    if (x >= 1) {
      return 1;
    }
    return Math.pow(2, -8 * x) * Math.sin((x * 8 - 0.75) * c4) + 1;
  }

  spiralPath(p) {
    const constrained = this.constrain(1.2 * p, 0, 1);
    const eased = this.ease(constrained, 1.8);
    const numberOfSpiralTurns = 6;
    const theta = 2 * Math.PI * numberOfSpiralTurns * Math.sqrt(eased);
    const r = 170 * Math.sqrt(eased);

    return new Vector2D(
      r * Math.cos(theta),
      r * Math.sin(theta) + this.startDotYOffset,
    );
  }

  rotate(v1, v2, p, orientation) {
    const middle = new Vector2D((v1.x + v2.x) / 2, (v1.y + v2.y) / 2);
    const dx = v1.x - middle.x;
    const dy = v1.y - middle.y;
    const angle = Math.atan2(dy, dx);
    const direction = orientation ? -1 : 1;
    const r = Math.sqrt(dx * dx + dy * dy);
    const bounce = Math.sin(p * Math.PI) * 0.05 * (1 - p);

    return new Vector2D(
      middle.x + r * (1 + bounce) * Math.cos(angle + direction * Math.PI * this.easeOutElastic(p)),
      middle.y + r * (1 + bounce) * Math.sin(angle + direction * Math.PI * this.easeOutElastic(p)),
    );
  }

  showProjectedDot(position, sizeFactor) {
    const t2 = this.constrain(this.map(this.time, this.changeEventTime, 1, 0, 1), 0, 1);
    const newCameraZ = this.cameraZ + this.ease(Math.pow(t2, 1.2), 1.8) * this.cameraTravelDistance;

    if (position.z > newCameraZ) {
      const dotDepthFromCamera = position.z - newCameraZ;
      const x = (this.viewZoom * position.x) / dotDepthFromCamera;
      const y = (this.viewZoom * position.y) / dotDepthFromCamera;
      const sw = (400 * sizeFactor) / dotDepthFromCamera;

      this.ctx.lineWidth = sw;
      this.ctx.beginPath();
      this.ctx.arc(x, y, 0.5, 0, Math.PI * 2);
      this.ctx.fill();
    }
  }

  drawTrail(t1) {
    for (let i = 0; i < this.trailLength; i += 1) {
      const f = this.map(i, 0, this.trailLength, 1.1, 0.1);
      const sw = (1.3 * (1 - t1) + 3.0 * Math.sin(Math.PI * t1)) * f;

      this.ctx.fillStyle = '#f6f9ff';
      this.ctx.lineWidth = sw;

      const pathTime = t1 - 0.00015 * i;
      const position = this.spiralPath(pathTime);
      const offset = new Vector2D(position.x + 5, position.y + 5);
      const rotated = this.rotate(
        position,
        offset,
        Math.sin(this.time * Math.PI * 2) * 0.5 + 0.5,
        i % 2 === 0,
      );

      this.ctx.beginPath();
      this.ctx.arc(rotated.x, rotated.y, sw / 2, 0, Math.PI * 2);
      this.ctx.fill();
    }
  }

  drawStartDot() {
    if (this.time > this.changeEventTime) {
      const dy = (this.cameraZ * this.startDotYOffset) / this.viewZoom;
      const position = new Vector3D(0, dy, this.cameraTravelDistance);
      this.showProjectedDot(position, 2.5);
    }
  }

  render() {
    this.ctx.fillStyle = '#05070f';
    this.ctx.fillRect(0, 0, this.width, this.height);

    this.ctx.save();
    this.ctx.translate(this.width / 2, this.height / 2);

    const t1 = this.constrain(this.map(this.time, 0, this.changeEventTime + 0.25, 0, 1), 0, 1);
    const t2 = this.constrain(this.map(this.time, this.changeEventTime, 1, 0, 1), 0, 1);

    this.ctx.rotate(-Math.PI * this.ease(t2, 2.7));
    this.drawTrail(t1);

    this.ctx.fillStyle = '#f7faff';
    for (const star of this.stars) {
      star.render(t1, this);
    }

    this.drawStartDot();
    this.ctx.restore();
  }

  pause() {
    this.timeline.pause();
  }

  resume() {
    this.timeline.play();
  }

  destroy() {
    this.timeline.kill();
  }
}

export default function Dashboard() {
  const navigate = useNavigate();
  const { user } = useUser();
  const surfaceRef = useRef(null);

  const effectiveRole = FEATURE_VISIBILITY.enforcedRole || user?.role;
  const capabilities = getRoleCapabilities(effectiveRole);

  useEffect(() => {
    const container = surfaceRef.current;
    if (!container) {
      return undefined;
    }

    const canvas = document.createElement('canvas');
    container.replaceChildren(canvas);

    let controller = null;

    const setupAnimation = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const width = window.innerWidth;
      const height = window.innerHeight;

      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;

      const ctx = canvas.getContext('2d');
      if (!ctx) {
        return;
      }

      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      if (controller) {
        controller.destroy();
      }

      controller = new AnimationController(ctx, width, height);
    };

    const handleResize = () => {
      setupAnimation();
    };

    const handleVisibility = () => {
      if (!controller) {
        return;
      }

      if (document.hidden) {
        controller.pause();
      } else {
        controller.resume();
      }
    };

    window.addEventListener('resize', handleResize);
    document.addEventListener('visibilitychange', handleVisibility);
    setupAnimation();

    return () => {
      window.removeEventListener('resize', handleResize);
      document.removeEventListener('visibilitychange', handleVisibility);
      if (controller) {
        controller.destroy();
      }
      container.replaceChildren();
    };
  }, []);

  const handleGetStarted = () => {
    if (!capabilities.canRunSimulation) {
      return;
    }
    navigate('/analysis', { state: { showWizard: true } });
  };

  const handleAbout = () => {
    navigate('/reports');
  };

  return (
    <div className="dashboard-page dashboard-dotted">
      <div ref={surfaceRef} className="dashboard-surface" aria-hidden="true" />

      <section className="dashboard-hero-shell" aria-label="Onyx hero">
        <h1 className="dashboard-onyx-title">Onyx</h1>

        <div className="dashboard-actions">
          <button
            type="button"
            className="dashboard-pill-button"
            onClick={handleGetStarted}
            disabled={!capabilities.canRunSimulation}
            title={!capabilities.canRunSimulation ? getPermissionReason(user?.role, 'runSimulation') : ''}
          >
            <span className="pill-label">Get Started</span>
          </button>

          <button type="button" className="dashboard-pill-button secondary" onClick={handleAbout}>
            <span className="pill-label">About</span>
          </button>
        </div>

        {!capabilities.canRunSimulation && (
          <p className="dashboard-permission-note">{getPermissionReason(user?.role, 'runSimulation')}</p>
        )}
      </section>

      <svg width="0" height="0" className="dashboard-glass-defs" aria-hidden="true">
        <defs>
          <filter
            id="container-glass"
            x="0%"
            y="0%"
            width="100%"
            height="100%"
            colorInterpolationFilters="sRGB"
          >
            <feTurbulence
              type="fractalNoise"
              baseFrequency="0.05 0.05"
              numOctaves="1"
              seed="1"
              result="turbulence"
            />
            <feGaussianBlur in="turbulence" stdDeviation="2" result="blurredNoise" />
            <feDisplacementMap
              in="SourceGraphic"
              in2="blurredNoise"
              scale="70"
              xChannelSelector="R"
              yChannelSelector="B"
              result="displaced"
            />
            <feGaussianBlur in="displaced" stdDeviation="4" result="finalBlur" />
            <feComposite in="finalBlur" in2="finalBlur" operator="over" />
          </filter>
        </defs>
      </svg>
    </div>
  );
}
