import { defineStore } from 'pinia';
import { ref, computed, watch } from 'vue';
import type {
  Tick,
  TickBufferConfig,
  TimelineKeyframe,
  GhostFrame,
  TimelineState,
  PredictionFrame,
} from '@/types';

// ============================================================================
// TickBuffer - Circular buffer for efficient tick storage
// ============================================================================

class TickBuffer {
  private buffer: Tick[];
  private head = 0;
  private tail = 0;
  private size = 0;
  private readonly maxSize: number;
  private readonly delta: number;
  private readonly circular: boolean;

  constructor(config: TickBufferConfig) {
    this.maxSize = config.maxSize;
    this.delta = config.delta;
    this.circular = config.circular;
    this.buffer = new Array(this.maxSize);
    this.size = 0;
  }

  push(tick: Tick): void {
    if (this.size < this.maxSize) {
      this.buffer[this.size++] = tick;
    } else if (this.circular) {
      this.buffer[this.tail] = tick;
      this.tail = (this.tail + 1) % this.maxSize;
      this.head = (this.head + 1) % this.maxSize;
    }
    // If not circular and full, oldest tick is discarded
  }

  get(index: number): Tick | undefined {
    if (index < 0 || index >= this.size) return undefined;
    return this.buffer[index];
  }

  getAll(): Tick[] {
    if (this.size === 0) return [];
    if (!this.circular || this.size < this.maxSize) {
      return this.buffer.slice(0, this.size);
    }
    // For circular buffer, return in chronological order
    const result: Tick[] = [];
    for (let i = 0; i < this.size; i++) {
      result.push(this.buffer[(this.head + i) % this.maxSize]);
    }
    return result;
  }

  getRange(from: number, to: number): Tick[] {
    const result: Tick[] = [];
    for (let i = from; i <= to && i < this.size; i++) {
      const tick = this.get(i);
      if (tick !== undefined) result.push(tick);
    }
    return result;
  }

  get newest(): Tick | undefined {
    if (this.size === 0) return undefined;
    return this.circular
      ? this.buffer[(this.tail - 1 + this.maxSize) % this.maxSize]
      : this.buffer[this.size - 1];
  }

  get oldest(): Tick | undefined {
    if (this.size === 0) return undefined;
    return this.circular ? this.buffer[this.head] : this.buffer[0];
  }

  get length(): number {
    return this.size;
  }

  clear(): void {
    this.buffer = new Array(this.maxSize);
    this.head = 0;
    this.tail = 0;
    this.size = 0;
  }

  resize(newMaxSize: number): void {
    const newBuffer = new Array(newMaxSize);
    const ticks = this.getAll();
    const copyCount = Math.min(ticks.length, newMaxSize);
    for (let i = 0; i < copyCount; i++) {
      newBuffer[i] = ticks[i];
    }
    this.buffer = newBuffer;
    this.maxSize = newMaxSize;
    this.size = Math.min(this.size, newMaxSize);
    this.head = 0;
    this.tail = copyCount < newMaxSize ? copyCount : 0;
  }
}

// ============================================================================
// Timeline Store
// ============================================================================

export function useTimelineStore() {
  return defineStore('timeline', () => {
    // -------------------------------------------------------------------------
    // State
    // -------------------------------------------------------------------------
    
    const currentTick = ref<Tick>(0);
    const isPlaying = ref(false);
    const playbackSpeed = ref(1); // multiplier: 0.5 = slow, 1 = normal, 2 = fast
    const loopPlayback = ref(false);
    const showGhosts = ref(true);
    const showPredictions = ref(false);
    const predictionConfidenceThreshold = ref(0.7);
    const autoKeyframeInterval = ref(100); // auto-create keyframe every N ticks

    // Tick Buffer Configuration
    const bufferConfig = ref<TickBufferConfig>({
      maxSize: 1000,
      delta: 1,
      circular: true,
    });

    // Tick Buffer Instance
    const tickBuffer = ref<TickBuffer>(
      new TickBuffer(bufferConfig.value)
    );

    // Keyframes
    const keyframes = ref<TimelineKeyframe[]>([]);

    // Ghost Frames (historical states for playback comparison)
    const ghostFrames = ref<GhostFrame[]>([]);

    // Prediction Frames (forecasted states)
    const predictionFrames = ref<PredictionFrame[]>([]);

    // Maximum tick value
    const maxTick = ref<Tick>(10000);

    // Playback interval reference
    let playbackInterval: ReturnType<typeof setInterval> | null = null;

    // -------------------------------------------------------------------------
    // Computed
    // -------------------------------------------------------------------------

    const hasNextTick = computed(() => currentTick.value < maxTick.value);
    const hasPreviousTick = computed(() => currentTick.value > 0);
    const isAtStart = computed(() => currentTick.value === 0);
    const isAtEnd = computed(() => currentTick.value >= maxTick.value);
    
    const tickProgress = computed(() => ({
      current: currentTick.value,
      total: maxTick.value,
      percentage: (currentTick.value / maxTick.value) * 100,
    }));

    const currentGhostFrames = computed(() =>
      ghostFrames.value.filter(gf => gf.tick <= currentTick.value)
    );

    const currentPredictionFrames = computed(() =>
      predictionFrames.value.filter(
        pf => pf.confidence >= predictionConfidenceThreshold.value
      )
    );

    const keyframeAtCurrentTick = computed(() =>
      keyframes.value.find(kf => kf.tick === currentTick.value)
    );

    const nearbyKeyframes = computed(() => {
      const tolerance = 50; // ticks
      return keyframes.value.filter(
        kf => Math.abs(kf.tick - currentTick.value) <= tolerance
      );
    });

    const bufferUsage = computed(() => ({
      used: tickBuffer.value.length,
      capacity: bufferConfig.value.maxSize,
      percentage: (tickBuffer.value.length / bufferConfig.value.maxSize) * 100,
    }));

    const totalKeyframes = computed(() => keyframes.value.length);
    const totalGhostFrames = computed(() => ghostFrames.value.length);
    const totalPredictionFrames = computed(() => predictionFrames.value.length);

    // -------------------------------------------------------------------------
    // Buffer Operations
    // -------------------------------------------------------------------------

    function configureBuffer(config: Partial<TickBufferConfig>): void {
      const newConfig = { ...bufferConfig.value, ...config };
      bufferConfig.value = newConfig;
      
      // Reinitialize buffer with new config
      tickBuffer.value = new TickBuffer(newConfig);
      
      // Re-populate with existing ticks if any
      const existingTicks = currentTicksInBuffer.value;
      existingTicks.forEach(tick => tickBuffer.value.push(tick));
    }

    function addTickToBuffer(tick: Tick): void {
      tickBuffer.value.push(tick);
    }

    function getTicksFromBuffer(from: number, to?: number): Tick[] {
      if (to === undefined) {
        // Get N most recent ticks
        const all = tickBuffer.value.getAll();
        return all.slice(-from);
      }
      return tickBuffer.value.getRange(from, to);
    }

    // Helper to track current ticks in buffer (for re-population)
    const currentTicksInBuffer = ref<Tick[]>([]);

    function recordTick(tick: Tick): void {
      addTickToBuffer(tick);
      
      // Track for re-population
      if (!currentTicksInBuffer.value.includes(tick)) {
        currentTicksInBuffer.value.push(tick);
        if (currentTicksInBuffer.value.length > bufferConfig.value.maxSize) {
          currentTicksInBuffer.value.shift();
        }
      }

      // Auto-keyframe creation
      if (
        autoKeyframeInterval.value > 0 &&
        tick % autoKeyframeInterval.value === 0
      ) {
        addAutoKeyframe(tick);
      }
    }

    // -------------------------------------------------------------------------
    // Playback Controls
    // -------------------------------------------------------------------------

    function play(): void {
      if (isPlaying.value) return;
      
      isPlaying.value = true;
      
      playbackInterval = setInterval(() => {
        const nextTick = currentTick.value + (1 * playbackSpeed.value);
        
        if (nextTick >= maxTick.value) {
          if (loopPlayback.value) {
            goToTick(0);
          } else {
            pause();
          }
        } else {
          goToTick(Math.floor(nextTick));
        }
      }, 100); // Base interval 100ms, adjusted by speed
    }

    function pause(): void {
      isPlaying.value = false;
      if (playbackInterval) {
        clearInterval(playbackInterval);
        playbackInterval = null;
      }
    }

    function togglePlayback(): void {
      if (isPlaying.value) {
        pause();
      } else {
        play();
      }
    }

    function stop(): void {
      pause();
      goToTick(0);
    }

    function goToTick(tick: Tick): void {
      const clampedTick = Math.max(0, Math.min(tick, maxTick.value));
      currentTick.value = clampedTick;
    }

    function goToNextTick(): void {
      if (hasNextTick.value) {
        currentTick.value += Math.ceil(1 * playbackSpeed.value);
      }
    }

    function goToPreviousTick(): void {
      if (hasPreviousTick.value) {
        currentTick.value -= Math.ceil(1 * playbackSpeed.value);
      }
    }

    function goToStart(): void {
      goToTick(0);
    }

    function goToEnd(): void {
      goToTick(maxTick.value);
    }

    function setSpeed(speed: number): void {
      playbackSpeed.value = Math.max(0.1, Math.min(10, speed));
    }

    function setMaxTick(tick: Tick): void {
      maxTick.value = Math.max(currentTick.value + 1, tick);
    }

    // -------------------------------------------------------------------------
    // Keyframe Management
    // -------------------------------------------------------------------------

    function addKeyframe(
      tick: Tick,
      label?: string,
      metadata?: Record<string, unknown>
    ): TimelineKeyframe {
      const keyframe: TimelineKeyframe = {
        id: `kf_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        tick,
        label: label || `Tick ${tick}`,
        timestamp: new Date().toISOString(),
        metadata,
        isAuto: false,
      };

      // Insert in sorted order
      const insertIndex = keyframes.value.findIndex(kf => kf.tick > tick);
      if (insertIndex === -1) {
        keyframes.value.push(keyframe);
      } else {
        keyframes.value.splice(insertIndex, 0, keyframe);
      }

      return keyframe;
    }

    function addAutoKeyframe(tick: Tick): TimelineKeyframe {
      return addKeyframe(tick, `Auto Tick ${tick}`, undefined);
    }

    function removeKeyframe(id: string): void {
      const index = keyframes.value.findIndex(kf => kf.id === id);
      if (index !== -1) {
        keyframes.value.splice(index, 1);
      }
    }

    function updateKeyframe(
      id: string,
      updates: Partial<Omit<TimelineKeyframe, 'id' | 'tick'>>
    ): void {
      const keyframe = keyframes.value.find(kf => kf.id === id);
      if (keyframe) {
        Object.assign(keyframe, updates);
      }
    }

    function getKeyframeAtTick(tick: Tick): TimelineKeyframe | undefined {
      return keyframes.value.find(kf => kf.tick === tick);
    }

    function getNearestKeyframe(tick: Tick): TimelineKeyframe | undefined {
      if (keyframes.value.length === 0) return undefined;
      
      let nearest = keyframes.value[0];
      let minDistance = Math.abs(nearest.tick - tick);
      
      for (const kf of keyframes.value) {
        const distance = Math.abs(kf.tick - tick);
        if (distance < minDistance) {
          minDistance = distance;
          nearest = kf;
        }
      }
      
      return nearest;
    }

    function clearKeyframes(): void {
      keyframes.value = [];
    }

    // -------------------------------------------------------------------------
    // Ghost Frame Management
    // -------------------------------------------------------------------------

    function addGhostFrame(
      tick: Tick,
      properties: Record<string, unknown>,
      position?: { x: number; y: number; z?: number },
      opacity?: number
    ): GhostFrame {
      const ghostFrame: GhostFrame = {
        tick,
        opacity: opacity ?? 0.3,
        position,
        properties,
      };

      // Insert in sorted order
      const insertIndex = ghostFrames.value.findIndex(gf => gf.tick > tick);
      if (insertIndex === -1) {
        ghostFrames.value.push(ghostFrame);
      } else {
        ghostFrames.value.splice(insertIndex, 0, ghostFrame);
      }

      return ghostFrame;
    }

    function removeGhostFramesAtTick(tick: Tick): void {
      ghostFrames.value = ghostFrames.value.filter(gf => gf.tick !== tick);
    }

    function clearGhostFrames(): void {
      ghostFrames.value = [];
    }

    function getGhostFramesInRange(fromTick: Tick, toTick: Tick): GhostFrame[] {
      return ghostFrames.value.filter(
        gf => gf.tick >= fromTick && gf.tick <= toTick
      );
    }

    function setGhostOpacity(tick: Tick, opacity: number): void {
      const frame = ghostFrames.value.find(gf => gf.tick === tick);
      if (frame) {
        frame.opacity = Math.max(0, Math.min(1, opacity));
      }
    }

    // -------------------------------------------------------------------------
    // Prediction Frame Management
    // -------------------------------------------------------------------------

    function addPredictionFrame(
      tick: Tick,
      properties: Record<string, unknown>,
      confidence: number,
      predictedBy: string
    ): PredictionFrame {
      const predictionFrame: PredictionFrame = {
        tick,
        confidence,
        predictedBy,
        properties,
      };

      // Insert in sorted order
      const insertIndex = predictionFrames.value.findIndex(pf => pf.tick > tick);
      if (insertIndex === -1) {
        predictionFrames.value.push(predictionFrame);
      } else {
        predictionFrames.value.splice(insertIndex, 0, predictionFrame);
      }

      return predictionFrame;
    }

    function clearPredictions(): void {
      predictionFrames.value = [];
    }

    function getPredictionsInRange(fromTick: Tick, toTick: Tick): PredictionFrame[] {
      return predictionFrames.value.filter(
        pf => pf.tick >= fromTick && pf.tick <= toTick
      );
    }

    // -------------------------------------------------------------------------
    // Serialization / Export
    // -------------------------------------------------------------------------

    function exportState(): TimelineState {
      return {
        currentTick: currentTick.value,
        isPlaying: isPlaying.value,
        playbackSpeed: playbackSpeed.value,
        keyframes: [...keyframes.value],
        ghostFrames: [...ghostFrames.value],
        bufferConfig: { ...bufferConfig.value },
      };
    }

    function importState(state: TimelineState): void {
      pause();
      
      currentTick.value = state.currentTick;
      isPlaying.value = state.isPlaying;
      playbackSpeed.value = state.playbackSpeed;
      keyframes.value = [...state.keyframes];
      ghostFrames.value = [...state.ghostFrames];
      bufferConfig.value = { ...state.bufferConfig };
      
      // Reinitialize buffer
      tickBuffer.value = new TickBuffer(bufferConfig.value);
    }

    // -------------------------------------------------------------------------
    // Reset
    // -------------------------------------------------------------------------

    function reset(): void {
      pause();
      
      currentTick.value = 0;
      isPlaying.value = false;
      playbackSpeed.value = 1;
      loopPlayback.value = false;
      showGhosts.value = true;
      showPredictions.value = false;
      
      bufferConfig.value = {
        maxSize: 1000,
        delta: 1,
        circular: true,
      };
      tickBuffer.value = new TickBuffer(bufferConfig.value);
      
      keyframes.value = [];
      ghostFrames.value = [];
      predictionFrames.value = [];
      maxTick.value = 10000;
    }

    // -------------------------------------------------------------------------
    // Return Store Interface
    // -------------------------------------------------------------------------

    return {
      // State
      currentTick,
      isPlaying,
      playbackSpeed,
      loopPlayback,
      showGhosts,
      showPredictions,
      predictionConfidenceThreshold,
      autoKeyframeInterval,
      bufferConfig,
      keyframes,
      ghostFrames,
      predictionFrames,
      maxTick,

      // Computed
      hasNextTick,
      hasPreviousTick,
      isAtStart,
      isAtEnd,
      tickProgress,
      currentGhostFrames,
      currentPredictionFrames,
      keyframeAtCurrentTick,
      nearbyKeyframes,
      bufferUsage,
      totalKeyframes,
      totalGhostFrames,
      totalPredictionFrames,

      // Buffer Operations
      configureBuffer,
      addTickToBuffer,
      getTicksFromBuffer,
      recordTick,

      // Playback Controls
      play,
      pause,
      togglePlayback,
      stop,
      goToTick,
      goToNextTick,
      goToPreviousTick,
      goToStart,
      goToEnd,
      setSpeed,
      setMaxTick,

      // Keyframe Management
      addKeyframe,
      addAutoKeyframe,
      removeKeyframe,
      updateKeyframe,
      getKeyframeAtTick,
      getNearestKeyframe,
      clearKeyframes,

      // Ghost Frame Management
      addGhostFrame,
      removeGhostFramesAtTick,
      clearGhostFrames,
      getGhostFramesInRange,
      setGhostOpacity,

      // Prediction Frame Management
      addPredictionFrame,
      clearPredictions,
      getPredictionsInRange,

      // Serialization
      exportState,
      importState,

      // Reset
      reset,
    };
  })();
}
