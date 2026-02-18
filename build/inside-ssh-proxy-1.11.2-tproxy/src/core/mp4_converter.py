"""MP4 conversion worker for RDP session recordings."""
import os
import re
import subprocess
import time
import logging
from datetime import datetime
from pathlib import Path
from sqlalchemy import and_
from src.core.database import SessionLocal, MP4ConversionQueue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - MP4Worker-%(process)d - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
PYRDP_CONVERT_PATH = "/opt/jumphost/venv-pyrdp-converter/bin/pyrdp-convert"
VENV_ACTIVATE = "source /opt/jumphost/venv-pyrdp-converter/bin/activate"
REPLAYS_DIR = "/var/log/jumphost/rdp_recordings/replays"
MP4_CACHE_DIR = "/var/log/jumphost/rdp_recordings/mp4_cache"
MAX_WORKERS = 2
POLL_INTERVAL = 5  # Check queue every 5 seconds
PROGRESS_REGEX = re.compile(r'(\d+)% \((\d+) of (\d+)\)')


class MP4ConversionWorker:
    """Worker process for MP4 conversion queue."""
    
    def __init__(self, worker_id: int):
        self.worker_id = worker_id
        self.current_session_id = None
        logger.info(f"Worker {worker_id} initialized")
        
        # Ensure MP4 cache directory exists
        os.makedirs(MP4_CACHE_DIR, exist_ok=True)
    
    def run(self):
        """Main worker loop - monitors queue and processes jobs."""
        logger.info(f"Worker {self.worker_id} started")
        
        while True:
            try:
                job = self._get_next_job()
                
                if job:
                    self.current_session_id = job.session_id
                    logger.info(f"Worker {self.worker_id} picked up job: {job.session_id}")
                    
                    try:
                        self._process_job(job)
                    except Exception as e:
                        logger.error(f"Error processing job {job.session_id}: {e}", exc_info=True)
                        self._mark_failed(job.session_id, str(e))
                    finally:
                        self.current_session_id = None
                else:
                    # No jobs available, sleep
                    time.sleep(POLL_INTERVAL)
                    
            except KeyboardInterrupt:
                logger.info(f"Worker {self.worker_id} shutting down")
                break
            except Exception as e:
                logger.error(f"Worker {self.worker_id} error: {e}", exc_info=True)
                time.sleep(POLL_INTERVAL)
    
    def _get_next_job(self):
        """Get next pending job from queue (priority-ordered)."""
        db = SessionLocal()
        try:
            # Check how many jobs are currently converting
            converting_count = db.query(MP4ConversionQueue).filter(
                MP4ConversionQueue.status == 'converting'
            ).count()
            
            if converting_count >= MAX_WORKERS:
                return None
            
            # Get highest priority pending job
            job = db.query(MP4ConversionQueue).filter(
                MP4ConversionQueue.status == 'pending'
            ).order_by(
                MP4ConversionQueue.priority.desc(),
                MP4ConversionQueue.created_at.asc()
            ).first()
            
            if job:
                # Mark as converting
                job.status = 'converting'
                job.started_at = datetime.utcnow()
                db.commit()
                db.refresh(job)
                return job
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting next job: {e}")
            db.rollback()
            return None
        finally:
            db.close()
    
    def _process_job(self, job):
        """Process MP4 conversion job."""
        session_id = job.session_id
        
        # Find .pyrdp file
        pyrdp_files = list(Path(REPLAYS_DIR).glob(f"*{session_id}*.pyrdp"))
        if not pyrdp_files:
            raise FileNotFoundError(f"No .pyrdp file found for session {session_id}")
        
        pyrdp_path = str(pyrdp_files[0])
        mp4_filename = f"{session_id}.mp4"
        mp4_path = os.path.join(MP4_CACHE_DIR, mp4_filename)
        
        logger.info(f"Converting {pyrdp_path} to {mp4_path}")
        
        # Build conversion command
        cmd = [
            'bash', '-c',
            f'{VENV_ACTIVATE} && '
            f'export QT_QPA_PLATFORM=offscreen && '
            f'{PYRDP_CONVERT_PATH} -f mp4 -o {mp4_path} {pyrdp_path}'
        ]
        
        # Start conversion process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Track progress
        for line in iter(process.stdout.readline, ''):
            if not line:
                break
            
            # Parse progress: "30% (2143 of 7005)"
            match = PROGRESS_REGEX.search(line)
            if match:
                percent = int(match.group(1))
                current = int(match.group(2))
                total = int(match.group(3))
                
                # Estimate ETA (rough calculation)
                elapsed = (datetime.utcnow() - job.started_at).total_seconds()
                if current > 0:
                    eta = int((elapsed / current) * (total - current))
                else:
                    eta = None
                
                self._update_progress(session_id, current, total, eta)
                logger.debug(f"Progress {session_id}: {percent}% ({current}/{total}), ETA: {eta}s")
        
        # Wait for completion
        return_code = process.wait()
        
        # pyrdp-convert creates file with prefix, find actual file
        if return_code == 0:
            # Find created MP4 file (may have prefix added by pyrdp-convert)
            mp4_dir = os.path.dirname(mp4_path)
            created_files = list(Path(mp4_dir).glob(f"*{session_id}*.mp4"))
            
            if created_files:
                actual_mp4_path = str(created_files[0])
                self._mark_completed(session_id, actual_mp4_path)
                logger.info(f"Successfully converted {session_id} to {actual_mp4_path}")
            else:
                raise RuntimeError(f"Conversion completed but MP4 file not found in {mp4_dir}")
        else:
            raise RuntimeError(f"Conversion failed with return code {return_code}")
    
    def _update_progress(self, session_id: str, progress: int, total: int, eta: int = None):
        """Update job progress in database."""
        db = SessionLocal()
        try:
            job = db.query(MP4ConversionQueue).filter(
                MP4ConversionQueue.session_id == session_id
            ).first()
            
            if job:
                job.progress = progress
                job.total = total
                if eta is not None:
                    job.eta_seconds = eta
                db.commit()
        except Exception as e:
            logger.error(f"Error updating progress: {e}")
            db.rollback()
        finally:
            db.close()
    
    def _mark_completed(self, session_id: str, mp4_path: str):
        """Mark job as completed."""
        db = SessionLocal()
        try:
            job = db.query(MP4ConversionQueue).filter(
                MP4ConversionQueue.session_id == session_id
            ).first()
            
            if job:
                job.status = 'completed'
                job.mp4_path = mp4_path
                job.completed_at = datetime.utcnow()
                job.progress = job.total  # Ensure 100%
                job.eta_seconds = 0
                db.commit()
        except Exception as e:
            logger.error(f"Error marking completed: {e}")
            db.rollback()
        finally:
            db.close()
    
    def _mark_failed(self, session_id: str, error_msg: str):
        """Mark job as failed."""
        db = SessionLocal()
        try:
            job = db.query(MP4ConversionQueue).filter(
                MP4ConversionQueue.session_id == session_id
            ).first()
            
            if job:
                job.status = 'failed'
                job.error_msg = error_msg
                job.completed_at = datetime.utcnow()
                db.commit()
        except Exception as e:
            logger.error(f"Error marking failed: {e}")
            db.rollback()
        finally:
            db.close()


def start_worker(worker_id: int):
    """Entry point for worker process."""
    worker = MP4ConversionWorker(worker_id)
    worker.run()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        worker_id = int(sys.argv[1])
    else:
        worker_id = 1
    
    start_worker(worker_id)
