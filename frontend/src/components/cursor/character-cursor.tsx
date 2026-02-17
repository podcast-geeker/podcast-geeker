'use client';

import React, { useEffect, useRef } from 'react';

interface CharacterCursorProps {
  characters?: string[];
  colors?: string[];
  cursorOffset?: { x: number; y: number };
  font?: string;
  maxParticles?: number;
  spawnIntervalMs?: number;
  characterLifeSpanFunction?: () => number;
  initialCharacterVelocityFunction?: () => { x: number; y: number };
  characterVelocityChangeFunctions?: {
    x_func: (age: number, lifeSpan: number) => number;
    y_func: (age: number, lifeSpan: number) => number;
  };
  characterScalingFunction?: (age: number, lifeSpan: number) => number;
  characterNewRotationDegreesFunction?: (
    age: number,
    lifeSpan: number
  ) => number;
  wrapperElement?: HTMLElement;
}

export function CharacterCursor({
  characters = ['h', 'e', 'l', 'l', 'o'],
  colors = ['#6622CC', '#A755C2', '#B07C9E', '#B59194', '#D2A1B8'],
  cursorOffset = { x: 0, y: 0 },
  font = '15px serif',
  maxParticles = 120,
  spawnIntervalMs = 16,
  characterLifeSpanFunction = () => Math.floor(Math.random() * 60 + 80),
  initialCharacterVelocityFunction = () => ({
    x: (Math.random() < 0.5 ? -1 : 1) * Math.random() * 5,
    y: (Math.random() < 0.5 ? -1 : 1) * Math.random() * 5,
  }),
  characterVelocityChangeFunctions = {
    x_func: () => (Math.random() < 0.5 ? -1 : 1) / 30,
    y_func: () => (Math.random() < 0.5 ? -1 : 1) / 15,
  },
  characterScalingFunction = (age, lifeSpan) =>
    Math.max(((lifeSpan - age) / lifeSpan) * 2, 0),
  characterNewRotationDegreesFunction = (age, lifeSpan) =>
    (lifeSpan - age) / 5,
  wrapperElement,
}: CharacterCursorProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const particlesRef = useRef<
    Array<{
      rotationSign: number;
      age: number;
      initialLifeSpan: number;
      lifeSpan: number;
      velocity: { x: number; y: number };
      position: { x: number; y: number };
      canv: HTMLCanvasElement;
      update: (context: CanvasRenderingContext2D) => void;
    }>
  >([]);
  const cursorRef = useRef({ x: 0, y: 0 });
  const animationFrameRef = useRef<number | null>(null);
  const isAnimatingRef = useRef(false);
  const lastSpawnTimeRef = useRef(0);
  const canvImagesRef = useRef<HTMLCanvasElement[]>([]);

  useEffect(() => {
    const prefersReducedMotion = window.matchMedia(
      '(prefers-reduced-motion: reduce)'
    );
    let canvas: HTMLCanvasElement | null = null;
    let context: CanvasRenderingContext2D | null = null;
    let width = window.innerWidth;
    let height = window.innerHeight;

    const randomPositiveOrNegativeOne = () => (Math.random() < 0.5 ? -1 : 1);

    class Particle {
      rotationSign: number;
      age: number;
      initialLifeSpan: number;
      lifeSpan: number;
      velocity: { x: number; y: number };
      position: { x: number; y: number };
      canv: HTMLCanvasElement;

      constructor(x: number, y: number, canvasItem: HTMLCanvasElement) {
        const lifeSpan = characterLifeSpanFunction();
        this.rotationSign = randomPositiveOrNegativeOne();
        this.age = 0;
        this.initialLifeSpan = lifeSpan;
        this.lifeSpan = lifeSpan;
        this.velocity = initialCharacterVelocityFunction();
        this.position = {
          x: x + cursorOffset.x,
          y: y + cursorOffset.y,
        };
        this.canv = canvasItem;
      }

      update(ctx: CanvasRenderingContext2D) {
        this.position.x += this.velocity.x;
        this.position.y += this.velocity.y;
        this.lifeSpan--;
        this.age++;

        this.velocity.x += characterVelocityChangeFunctions.x_func(
          this.age,
          this.initialLifeSpan
        );
        this.velocity.y += characterVelocityChangeFunctions.y_func(
          this.age,
          this.initialLifeSpan
        );

        const scale = characterScalingFunction(this.age, this.initialLifeSpan);

        const degrees =
          this.rotationSign *
          characterNewRotationDegreesFunction(this.age, this.initialLifeSpan);
        const radians = degrees * 0.0174533;

        ctx.translate(this.position.x, this.position.y);
        ctx.rotate(radians);

        ctx.drawImage(
          this.canv,
          (-this.canv.width / 2) * scale,
          -this.canv.height / 2,
          this.canv.width * scale,
          this.canv.height * scale
        );

        ctx.rotate(-radians);
        ctx.translate(-this.position.x, -this.position.y);
      }
    }

    const init = () => {
      const finePointer = window.matchMedia('(pointer: fine)');
      if (prefersReducedMotion.matches) {
        return false;
      }
      if (!finePointer.matches) {
        return false;
      }

      canvas = canvasRef.current;
      if (!canvas) return;

      context = canvas.getContext('2d');
      if (!context) return;

      canvas.style.top = '0px';
      canvas.style.left = '0px';
      canvas.style.pointerEvents = 'none';
      canvas.style.zIndex = '9999';

      if (wrapperElement) {
        canvas.style.position = 'absolute';
        wrapperElement.appendChild(canvas);
        canvas.width = wrapperElement.clientWidth;
        canvas.height = wrapperElement.clientHeight;
      } else {
        canvas.style.position = 'fixed';
        document.body.appendChild(canvas);
        canvas.width = width;
        canvas.height = height;
      }

      context.font = font;
      context.textBaseline = 'middle';
      context.textAlign = 'center';

      characters.forEach((char) => {
        const measurements = context!.measureText(char);
        const bgCanvas = document.createElement('canvas');
        const bgContext = bgCanvas.getContext('2d');

        if (bgContext) {
          bgCanvas.width = measurements.width;
          bgCanvas.height = measurements.actualBoundingBoxAscent * 2.5;

          bgContext.textAlign = 'center';
          bgContext.font = font;
          bgContext.textBaseline = 'middle';
          const randomColor =
            colors[Math.floor(Math.random() * colors.length)];
          bgContext.fillStyle = randomColor;

          bgContext.fillText(
            char,
            bgCanvas.width / 2,
            measurements.actualBoundingBoxAscent
          );

          canvImagesRef.current.push(bgCanvas);
        }
      });

      bindEvents();
    };

    const bindEvents = () => {
      const element = wrapperElement || document.body;
      element.addEventListener('mousemove', onMouseMove, { passive: true });
      element.addEventListener('touchmove', onTouchMove, { passive: true });
      element.addEventListener('touchstart', onTouchMove, { passive: true });
      window.addEventListener('resize', onWindowResize);
    };

    const onWindowResize = () => {
      width = window.innerWidth;
      height = window.innerHeight;

      if (!canvasRef.current) return;

      if (wrapperElement) {
        canvasRef.current.width = wrapperElement.clientWidth;
        canvasRef.current.height = wrapperElement.clientHeight;
      } else {
        canvasRef.current.width = width;
        canvasRef.current.height = height;
      }
    };

    const onTouchMove = (e: TouchEvent) => {
      const imgs = canvImagesRef.current;
      if (imgs.length === 0) return;

      if (e.touches.length > 0) {
        for (let i = 0; i < e.touches.length; i++) {
          addParticle(
            e.touches[i].clientX,
            e.touches[i].clientY,
            imgs[Math.floor(Math.random() * imgs.length)]
          );
        }
      }
    };

    const onMouseMove = (e: MouseEvent) => {
      const imgs = canvImagesRef.current;
      if (imgs.length === 0) return;

      if (wrapperElement) {
        const boundingRect = wrapperElement.getBoundingClientRect();
        cursorRef.current.x = e.clientX - boundingRect.left;
        cursorRef.current.y = e.clientY - boundingRect.top;
      } else {
        cursorRef.current.x = e.clientX;
        cursorRef.current.y = e.clientY;
      }

      const now = performance.now();
      if (now - lastSpawnTimeRef.current < spawnIntervalMs) {
        return;
      }
      lastSpawnTimeRef.current = now;

      addParticle(
        cursorRef.current.x,
        cursorRef.current.y,
        imgs[Math.floor(Math.random() * imgs.length)]
      );
    };

    const addParticle = (
      x: number,
      y: number,
      img: HTMLCanvasElement
    ) => {
      if (particlesRef.current.length >= maxParticles) {
        particlesRef.current.shift();
      }
      particlesRef.current.push(new Particle(x, y, img));
      startLoop();
    };

    const updateParticles = () => {
      if (!canvas || !context) return;

      if (particlesRef.current.length === 0) {
        return;
      }

      context.clearRect(0, 0, canvas.width, canvas.height);

      for (let i = 0; i < particlesRef.current.length; i++) {
        particlesRef.current[i].update(context);
      }

      for (let i = particlesRef.current.length - 1; i >= 0; i--) {
        if (particlesRef.current[i].lifeSpan < 0) {
          particlesRef.current.splice(i, 1);
        }
      }

      if (particlesRef.current.length === 0) {
        context.clearRect(0, 0, canvas.width, canvas.height);
      }
    };

    const loop = () => {
      updateParticles();
      if (particlesRef.current.length > 0) {
        animationFrameRef.current = requestAnimationFrame(loop);
      } else {
        isAnimatingRef.current = false;
        animationFrameRef.current = null;
      }
    };

    const startLoop = () => {
      if (isAnimatingRef.current) {
        return;
      }
      isAnimatingRef.current = true;
      animationFrameRef.current = requestAnimationFrame(loop);
    };

    init();

    return () => {
      if (canvas) {
        canvas.remove();
      }
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      const element = wrapperElement || document.body;
      element.removeEventListener('mousemove', onMouseMove);
      element.removeEventListener('touchmove', onTouchMove);
      element.removeEventListener('touchstart', onTouchMove);
      window.removeEventListener('resize', onWindowResize);
    };
  }, [
    characters,
    colors,
    cursorOffset,
    font,
    maxParticles,
    spawnIntervalMs,
    characterLifeSpanFunction,
    initialCharacterVelocityFunction,
    characterVelocityChangeFunctions,
    characterScalingFunction,
    characterNewRotationDegreesFunction,
    wrapperElement,
  ]);

  return <canvas ref={canvasRef} />;
}
