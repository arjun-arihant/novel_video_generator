/"""
Progress tracking and callback system for pipeline operations.

Provides a comprehensive progress tracking system with support for:
- Nested progress tracking
- Callbacks for progress updates
- ETA calculation
- Stage-based progress
"""

import time
from dataclasses import dataclass, field
from typing import Optional, Callable, List, Dict, Any
from enum import Enum


class ProgressStage(Enum):
    """Pipeline stages for progress tracking."""
    INITIALIZING = "initializing"
    EXTRACTING_SCENES = "extracting_scenes"
    GENERATING_IMAGES = "generating_images"
    GENERATING_AUDIO = "generating_audio"
    COMPOSING_VIDEO = "composing_video"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ProgressInfo:
    """Information about current progress."""
    stage: ProgressStage
    stage_name: str
    current: int
    total: int
    percentage: float
    eta_seconds: Optional[float]
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_complete(self) -> bool:
        """Check if the current stage is complete."""
        return self.current >= self.total


class ProgressTracker:
    """
    Tracks progress through pipeline stages.
    
    Example:
        tracker = ProgressTracker(total_scenes=5)
        tracker.on_progress = lambda p: print(f"{p.percentage}%")
        
        tracker.start_stage(ProgressStage.GENERATING_IMAGES, 5)
        for i in range(5):
            # Do work...
            tracker.update(i + 1, f"Generated image {i+1}")
        tracker.complete_stage()
    """
    
    def __init__(
        self,
        total_scenes: int = 0,
        on_progress: Optional[Callable[[ProgressInfo], None]] = None,
        on_stage_change: Optional[Callable[[ProgressStage, ProgressStage], None]] = None
    ):
        self.total_scenes = total_scenes
        self.on_progress = on_progress
        self.on_stage_change = on_stage_change
        
        self._current_stage: Optional[ProgressStage] = None
        self._stage_start_time: Optional[float] = None
        self._stage_progress: int = 0
        self._stage_total: int = 0
        self._history: List[ProgressInfo] = []
        self._stage_weights: Dict[ProgressStage, float] = {
            ProgressStage.EXTRACTING_SCENES: 0.15,
            ProgressStage.GENERATING_IMAGES: 0.35,
            ProgressStage.GENERATING_AUDIO: 0.25,
            ProgressStage.COMPOSING_VIDEO: 0.20,
            ProgressStage.FINALIZING: 0.05
        }
    
    def start_stage(
        self, 
        stage: ProgressStage, 
        total: int = 1,
        message: str = ""
    ) -> None:
        """Start a new progress stage."""
        previous_stage = self._current_stage
        self._current_stage = stage
        self._stage_start_time = time.time()
        self._stage_progress = 0
        self._stage_total = total
        
        if self.on_stage_change and previous_stage:
            self.on_stage_change(previous_stage, stage)
        
        self._notify(message or f"Starting {stage.value}")
    
    def update(
        self, 
        current: int, 
        message: str = "",
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update progress within the current stage."""
        self._stage_progress = current
        self._notify(message, details)
    
    def increment(self, message: str = "", details: Optional[Dict[str, Any]] = None) -> None:
        """Increment progress by 1."""
        self._stage_progress += 1
        self._notify(message, details)
    
    def complete_stage(self, message: str = "") -> None:
        """Mark the current stage as complete."""
        self._stage_progress = self._stage_total
        self._notify(message or f"Completed {self._current_stage.value}")
    
    def _calculate_eta(self) -> Optional[float]:
        """Calculate estimated time remaining."""
        if not self._stage_start_time or self._stage_progress == 0:
            return None
        
        elapsed = time.time() - self._stage_start_time
        rate = elapsed / self._stage_progress
        remaining = self._stage_total - self._stage_progress
        
        return rate * remaining
    
    def _calculate_overall_percentage(self) -> float:
        """Calculate overall pipeline percentage."""
        if not self._current_stage:
            return 0.0
        
        # Get weight for current stage
        weight = self._stage_weights.get(self._current_stage, 0.1)
        
        # Calculate completed weight
        completed_weight = sum(
            self._stage_weights.get(stage, 0) 
            for stage in ProgressStage 
            if stage < self._current_stage
        )
        
        # Add current stage progress
        if self._stage_total > 0:
            stage_progress = self._stage_progress / self._stage_total
        else:
            stage_progress = 0
        
        total = (completed_weight + weight * stage_progress) * 100
        return min(100.0, max(0.0, total))
    
    def _notify(
        self, 
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Notify progress callback."""
        if not self.on_progress or not self._current_stage:
            return
        
        percentage = self._calculate_overall_percentage()
        
        info = ProgressInfo(
            stage=self._current_stage,
            stage_name=self._current_stage.value,
            current=self._stage_progress,
            total=self._stage_total,
            percentage=percentage,
            eta_seconds=self._calculate_eta(),
            message=message,
            details=details or {}
        )
        
        self._history.append(info)
        self.on_progress(info)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the progress history."""
        if not self._history:
            return {}
        
        first = self._history[0]
        last = self._history[-1]
        
        return {
            'total_updates': len(self._history),
            'start_stage': first.stage.value,
            'current_stage': last.stage.value,
            'overall_percentage': last.percentage,
            'duration_seconds': time.time() - (self._stage_start_time or time.time())
        }


class ProgressCallback:
    """
    Helper class for creating progress callbacks.
    
    Provides common callback patterns like console output,
    file logging, or HTTP updates.
    """
    
    @staticmethod
    def console_output(format: str = "{percentage}% | {stage_name}: {message}") -> Callable[[ProgressInfo], None]:
        """Create a console output callback."""
        def callback(info: ProgressInfo):
            print(format.format(
                percentage=f"{info.percentage:.1f}",
                stage_name=info.stage_name,
                message=info.message,
                current=info.current,
                total=info.total,
                eta=f"{info.eta_seconds:.0f}s" if info.eta_seconds else "N/A"
            ))
        return callback
    
    @staticmethod
    def file_logger(path: str) -> Callable[[ProgressInfo], None]:
        """Create a file logging callback."""
        import json
        
        def callback(info: ProgressInfo):
            with open(path, 'a') as f:
                data = {
                    'timestamp': time.time(),
                    'stage': info.stage_name,
                    'percentage': info.percentage,
                    'message': info.message
                }
                f.write(json.dumps(data) + '\n')
        
        return callback
    
    @staticmethod
    def multi(*callbacks: Callable[[ProgressInfo], None]) -> Callable[[ProgressInfo], None]:
        """Combine multiple callbacks."""
        def combined(info: ProgressInfo):
            for cb in callbacks:
                try:
                    cb(info)
                except Exception as e:
                    print(f"Progress callback error: {e}")
        
        return combined


# Convenience functions for common patterns

def create_progress_bar(width: int = 40) -> Callable[[ProgressInfo], None]:
    """Create a progress bar callback for console output."""
    def callback(info: ProgressInfo):
        filled = int(width * info.percentage / 100)
        bar = '=' * filled + '-' * (width - filled)
        eta_str = f"{info.eta_seconds:.0f}s" if info.eta_seconds else "N/A"
        
        print(f'\r[{bar}] {info.percentage:.1f}% | {info.stage_name}: {info.message} (ETA: {eta_str})', 
              end='', flush=True)
        
        if info.percentage >= 100:
            print()  # New line when complete
    
    return callback
