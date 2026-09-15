import tobii_research as tr
import time
import csv
import numpy as np
import tkinter as tk
from tkinter import Canvas
from PIL import Image, ImageDraw, ImageTk
from pathlib import Path
from typing import Any, Callable

TARGET_DELAY = 1.0
TARGET_DURATION = 1.5
INTER_POINT_DELAY = 0.5
MOVEMENT_DURATION = 0.5

# ==================== VISUAL STIMULUS CLASS ====================
class CalibrationDisplay:
    """Full-screen display for calibration/validation points"""

    def __init__(self, width=1920, height=1080, dot_size=20):
        self.width = width
        self.height = height
        self.dot_size = dot_size
        self.root = None
        self.canvas = None

    def create_window(self):
        """Create full-screen grey window"""
        self.root = tk.Tk()
        self.root.attributes('-fullscreen', True)
        self.root.configure(bg='grey50')

        # Get actual screen dimensions
        self.width = self.root.winfo_screenwidth()
        self.height = self.root.winfo_screenheight()

        self.canvas = Canvas(self.root, bg='grey50', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.root.update()

    def show_dot(self, x_norm, y_norm, duration=1.0):
        """
        Show a dot at normalized screen coordinates (0-1)
        x_norm, y_norm: normalized coordinates (0=left/top, 1=right/bottom)
        duration: how long to show the dot in seconds
        """
        # Convert normalized coordinates to pixels
        x_px = int(x_norm * self.width)
        y_px = int(y_norm * self.height)

        # Clear canvas
        self.canvas.delete("all")

        # Draw dot (red circle)
        self.canvas.create_oval(
            x_px - self.dot_size, y_px - self.dot_size,
            x_px + self.dot_size, y_px + self.dot_size,
            fill='red', outline='darkred', width=2
        )

        # Draw crosshair
        self.canvas.create_line(x_px - 10, y_px, x_px + 10, y_px, fill='red', width=2)
        self.canvas.create_line(x_px, y_px - 10, x_px, y_px + 10, fill='red', width=2)

        self.canvas.update()
        time.sleep(duration)

    def move_dot(self, start_point, end_point, duration=MOVEMENT_DURATION, steps=30):
        """Animate the target between two normalized screen positions."""
        if start_point is None:
            self.show_dot(end_point[0], end_point[1], duration=0)
            return

        step_delay = duration / max(1, steps)
        for step in range(1, steps + 1):
            progress = step / steps
            x_norm = start_point[0] + (end_point[0] - start_point[0]) * progress
            y_norm = start_point[1] + (end_point[1] - start_point[1]) * progress
            self.show_dot(x_norm, y_norm, duration=0)
            time.sleep(step_delay)

    def show_message(self, message, duration=2.0):
        """Show a text message"""
        self.canvas.delete("all")
        self.canvas.create_text(
            self.width // 2, self.height // 2,
            text=message, font=("Arial", 48), fill='white'
        )
        self.canvas.update()
        time.sleep(duration)

    def close(self):
        """Close the display window"""
        if self.root:
            self.root.destroy()
            self.root = None
            self.canvas = None

# ==================== VALIDATION DIAGNOSTIC DIALOG ====================
class ValidationDiagnosticDialog:
    """Dialog window to display validation results and get approval"""

    def __init__(self, validation_data, mean_accuracy, std_accuracy):
        self.validation_data = validation_data
        self.mean_accuracy = mean_accuracy
        self.std_accuracy = std_accuracy
        self.approved = None
        self.root = None

    def draw_plot(self, width=1200, height=900):
        """Draw validation plot on PIL image"""
        # Create image with white background
        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)

        # Margins
        margin = 80
        plot_width = width - 2 * margin
        plot_height = height - 2 * margin - 80  # Extra space for title

        # Draw plot background
        draw.rectangle(
            [margin, margin + 80, margin + plot_width, margin + 80 + plot_height],
            outline='black', width=2
        )

        # Draw grid
        grid_count = 10
        for i in range(grid_count + 1):
            x = margin + (i / grid_count) * plot_width
            y = margin + 80 + (i / grid_count) * plot_height
            draw.line([(x, margin + 80), (x, margin + 80 + plot_height)], fill='lightgray', width=1)
            draw.line([(margin, y), (margin + plot_width, y)], fill='lightgray', width=1)

        # Draw axes labels
        draw.text((margin - 40, margin + 80 + plot_height + 10), "0.0", fill='black')
        draw.text((margin + plot_width - 20, margin + 80 + plot_height + 10), "1.0", fill='black')
        draw.text((margin - 30, margin + 70), "1.0", fill='black')
        draw.text((margin - 30, margin + 80 + plot_height - 20), "0.0", fill='black')

        # Plot validation points
        point_size = 8
        line_width = 2

        for idx, item in enumerate(self.validation_data):
            target = item['target']
            gaze = item['gaze']
            accuracy = item['accuracy']

            # Skip if invalid data
            if (np.isnan(accuracy) or np.isnan(gaze[0]) or np.isnan(gaze[1]) or
                target[0] < 0 or target[0] > 1 or target[1] < 0 or target[1] > 1 or
                gaze[0] < 0 or gaze[0] > 1 or gaze[1] < 0 or gaze[1] > 1):
                print(f"  Skipping invalid data for point {idx+1}: target={target}, gaze={gaze}, accuracy={accuracy}")
                continue

            # Convert normalized coordinates to pixel coordinates
            target_px = (
                margin + target[0] * plot_width,
                margin + 80 + target[1] * plot_height
            )
            gaze_px = (
                margin + gaze[0] * plot_width,
                margin + 80 + gaze[1] * plot_height
            )

            # Draw error circle (red dotted) - safely handle accuracy
            circle_radius = max(2, int(max(0, min(accuracy, 0.2)) * plot_width))
            draw.ellipse(
                [target_px[0] - circle_radius, target_px[1] - circle_radius,
                 target_px[0] + circle_radius, target_px[1] + circle_radius],
                outline='red', width=1
            )

            # Draw error line (blue)
            draw.line(
                [target_px[0], target_px[1], gaze_px[0], gaze_px[1]],
                fill='blue', width=line_width
            )

            # Draw target point (green circle)
            draw.ellipse(
                [target_px[0] - point_size, target_px[1] - point_size,
                 target_px[0] + point_size, target_px[1] + point_size],
                outline='darkgreen', width=2
            )

            # Draw fixation point (red X)
            cross_size = point_size
            draw.line(
                [gaze_px[0] - cross_size, gaze_px[1] - cross_size,
                 gaze_px[0] + cross_size, gaze_px[1] + cross_size],
                fill='red', width=2
            )
            draw.line(
                [gaze_px[0] - cross_size, gaze_px[1] + cross_size,
                 gaze_px[0] + cross_size, gaze_px[1] - cross_size],
                fill='red', width=2
            )

            # Draw point number
            draw.text(
                (target_px[0] - 8, target_px[1] - 18),
                str(idx + 1),
                fill='darkgreen'
            )

        # Draw title with statistics - handle NaN values
        if np.isnan(self.mean_accuracy):
            title = "Validation Review - [WARNING] No valid data collected"
        else:
            title = f"Validation Review - Mean Error: {self.mean_accuracy:.4f} | Std Dev: {self.std_accuracy:.4f}"
        draw.text((20, 20), title, fill='black')

        # Draw legend
        legend_y = height - 60
        draw.text((20, legend_y), "Legend:", fill='black', font=None)

        # Green circle for target
        draw.ellipse([40, legend_y + 20, 50, legend_y + 30], outline='darkgreen', width=2)
        draw.text((55, legend_y + 18), "Target", fill='black')

        # Red X for fixation
        draw.line([75, legend_y + 20, 85, legend_y + 30], fill='red', width=2)
        draw.line([75, legend_y + 30, 85, legend_y + 20], fill='red', width=2)
        draw.text((90, legend_y + 18), "Fixation", fill='black')

        # Blue line for error
        draw.line([155, legend_y + 25, 175, legend_y + 25], fill='blue', width=2)
        draw.text((180, legend_y + 18), "Error Vector", fill='black')

        return img

    def show(self):
        """Show diagnostic dialog and wait for approval"""
        self.root = tk.Tk()
        self.root.title("Validation Review")
        self.root.geometry("1100x850")
        self.root.protocol("WM_DELETE_WINDOW", self.retry)

        # Update window before creating PhotoImage to ensure proper initialization
        self.root.update_idletasks()

        # Create main frame
        main_frame = tk.Frame(self.root, bg='white')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Draw and display plot - keep references alive!
        self.plot_img = self.draw_plot(width=1000, height=650)
        self.photo = ImageTk.PhotoImage(self.plot_img)

        img_label = tk.Label(main_frame, image=self.photo, bg='white')
        img_label.pack(pady=10)

        # Instructions
        instructions = tk.Label(
            main_frame,
            text="GREEN circles = Target locations | RED X = Eye fixations\n"
                 "BLUE lines = Error vectors | If RED X marks are close to GREEN circles, validation looks good.",
            font=("Arial", 10),
            bg='white'
        )
        instructions.pack(pady=5)

        # Button frame
        button_frame = tk.Frame(main_frame, bg='white')
        button_frame.pack(pady=20)

        ok_button = tk.Button(
            button_frame,
            text="[OK] Accept Validation",
            font=("Arial", 14, "bold"),
            bg='green',
            fg='white',
            padx=20,
            pady=10,
            command=self.approve
        )
        ok_button.pack(side=tk.LEFT, padx=10)

        retry_button = tk.Button(
            button_frame,
            text="[RETRY] Restart Full Process",
            font=("Arial", 14, "bold"),
            bg='red',
            fg='white',
            padx=20,
            pady=10,
            command=self.retry
        )
        retry_button.pack(side=tk.LEFT, padx=10)

        # Make window modal
        self.root.wait_window()

        return self.approved

    def approve(self):
        """User clicked OK"""
        self.approved = True
        self.root.destroy()

    def retry(self):
        """User clicked RETRY"""
        self.approved = False
        self.root.destroy()

def find_eyetracker():
    eye_trackers = tr.find_all_eyetrackers()
    if not eye_trackers:
        raise RuntimeError("No eye trackers found.")

    tracker = eye_trackers[0]
    print(f"Eye tracker found: {tracker.model}")
    return tracker


def run_calibration_validation(my_eyetracker=None) -> object:
    if my_eyetracker is None:
        my_eyetracker = find_eyetracker()

    calibration_approved = False

    while not calibration_approved:
        display = CalibrationDisplay(dot_size=30)
        try:
            display.create_window()
            calibration_approved = _run_calibration_validation_attempt(my_eyetracker, display)
        except Exception as exc:
            print(f"\n[ERROR] Calibration/validation attempt failed: {exc}")
            print("Restarting calibration and validation...")
            calibration_approved = False
        finally:
            try:
                display.close()
            except tk.TclError:
                pass

    return my_eyetracker


def _run_calibration_validation_attempt(my_eyetracker, display: CalibrationDisplay) -> bool:
    print("\n" + "="*50)
    print("STARTING 9-POINT CALIBRATION")
    print("="*50)

    calibration = tr.ScreenBasedCalibration(my_eyetracker)
    calibration.enter_calibration_mode()

    try:
        calibration_points = [
            (0.1, 0.1), (0.5, 0.1), (0.9, 0.1),
            (0.1, 0.5), (0.5, 0.5), (0.9, 0.5),
            (0.1, 0.9), (0.5, 0.9), (0.9, 0.9)
        ]

        previous_point = None
        for idx, point in enumerate(calibration_points, 1):
            print(f"\n[{idx}/9] Calibration point ({point[0]}, {point[1]})")
            display.move_dot(previous_point, point)
            previous_point = point
            display.show_dot(point[0], point[1], duration=TARGET_DELAY)
            print("Collecting calibration data...")
            collection_status = calibration.collect_data(point[0], point[1])
            if collection_status != tr.CALIBRATION_STATUS_SUCCESS:
                print(f"Collection returned {collection_status}; retrying this point once...")
                collection_status = calibration.collect_data(point[0], point[1])
            print(f"Collection status: {collection_status}")
            time.sleep(INTER_POINT_DELAY)

        display.show_message("Calibration complete!\nComputing...", duration=1.0)
        print("\nComputing calibration...")
        calibration_result = calibration.compute_and_apply()
        print(f"Calibration status: {calibration_result.status}")

        if calibration_result.status == tr.CALIBRATION_STATUS_SUCCESS:
            print("[OK] Calibration successful!")
            display.show_message("[OK] Calibration Successful!", duration=2.0)
        else:
            print("[FAIL] Calibration failed. Some points may need recalibration.")
            display.show_message("[FAIL] Calibration Failed", duration=2.0)
    finally:
        calibration.leave_calibration_mode()

    if calibration_result.status != tr.CALIBRATION_STATUS_SUCCESS:
        print("Restarting from calibration because calibration was not applied successfully.")
        return False

    print("\n" + "="*50)
    print("STARTING 9-POINT VALIDATION")
    print("="*50)

    display.show_message("Starting Validation...", duration=1.0)
    validation_points = [
        (0.2, 0.2), (0.5, 0.2), (0.8, 0.2),
        (0.2, 0.5), (0.5, 0.5), (0.8, 0.5),
        (0.2, 0.8), (0.5, 0.8), (0.8, 0.8)
    ]
    validation_data = []
    validation_samples = {point: [] for point in validation_points}
    validation_state = {"collecting": False, "point": None}

    def validation_gaze_callback(gaze_data):
        current_point = validation_state["point"]
        if validation_state["collecting"] and current_point is not None:
            left_point = gaze_data.get('left_gaze_point_on_display_area')
            right_point = gaze_data.get('right_gaze_point_on_display_area')
            left_valid = gaze_data.get('left_gaze_point_validity', 0) == 1
            right_valid = gaze_data.get('right_gaze_point_validity', 0) == 1

            valid_points = []
            if left_valid and left_point and np.isfinite(left_point[0]) and np.isfinite(left_point[1]):
                valid_points.append(left_point)
            if right_valid and right_point and np.isfinite(right_point[0]) and np.isfinite(right_point[1]):
                valid_points.append(right_point)

            if valid_points:
                avg_x = np.mean([point[0] for point in valid_points])
                avg_y = np.mean([point[1] for point in valid_points])
                validation_samples[current_point].append((avg_x, avg_y))

    my_eyetracker.subscribe_to(tr.EYETRACKER_GAZE_DATA, validation_gaze_callback, as_dictionary=True)

    try:
        previous_point = None
        for idx, point in enumerate(validation_points, 1):
            print(f"\n[{idx}/9] Validation point ({point[0]}, {point[1]})")
            validation_state["point"] = point
            validation_samples[point] = []
            display.move_dot(previous_point, point)
            previous_point = point
            display.show_dot(point[0], point[1], duration=TARGET_DELAY)
            validation_state["collecting"] = True
            time.sleep(TARGET_DURATION)
            validation_state["collecting"] = False
            time.sleep(INTER_POINT_DELAY)

            print(f"  Collected {len(validation_samples[point])} gaze samples")

            if validation_samples[point]:
                avg_x = np.mean([s[0] for s in validation_samples[point]])
                avg_y = np.mean([s[1] for s in validation_samples[point]])
                accuracy = np.sqrt((avg_x - point[0])**2 + (avg_y - point[1])**2)
                print(f"  Recorded gaze: ({avg_x:.3f}, {avg_y:.3f}), Accuracy: {accuracy:.3f}")
                validation_data.append({
                    'target': point,
                    'gaze': (avg_x, avg_y),
                    'accuracy': accuracy
                })
            else:
                print(f"  [FAIL] No samples collected for this point")
    finally:
        validation_state["collecting"] = False
        try:
            my_eyetracker.unsubscribe_from(tr.EYETRACKER_GAZE_DATA, validation_gaze_callback)
        except Exception as exc:
            print(f"Warning: could not unsubscribe validation callback cleanly: {exc}")

    display.show_message("Validation complete!", duration=2.0)
    display.close()

    print("\n" + "="*50)
    print("VALIDATION REVIEW")
    print("="*50)

    if validation_data:
        accuracies = [item['accuracy'] for item in validation_data]
        valid_accuracies = [acc for acc in accuracies if not np.isnan(acc)]

        if valid_accuracies:
            mean_accuracy = np.mean(valid_accuracies)
            std_accuracy = np.std(valid_accuracies)
            print("\nValidation Statistics:")
            print(f"  Mean accuracy: {mean_accuracy:.4f}")
            print(f"  Std accuracy: {std_accuracy:.4f}")
            print(f"  Max accuracy: {np.max(valid_accuracies):.4f}")
            print(f"  Min accuracy: {np.min(valid_accuracies):.4f}")

            dialog = ValidationDiagnosticDialog(validation_data, mean_accuracy, std_accuracy)
            approved = dialog.show()
            if not approved:
                print("Validation rejected. Restarting calibration and validation...")
            return approved is True
        else:
            print("\n[ERROR] No valid gaze data collected during validation!")
            print("Restarting calibration and validation...")
            return False

    print("\n[ERROR] Validation data is empty - no points were recorded!")
    print("Restarting calibration and validation...")
    return False


class GazeRecorder:
    def __init__(
        self,
        my_eyetracker,
        output_file: str | Path = "tobii_gaze_data.csv",
        metadata: dict[str, Any] | None = None,
        scenario_time_source: Callable[[], float] | None = None,
        logtime_source: Callable[[], float] | None = None,
    ):
        self.my_eyetracker = my_eyetracker
        self.output_file = Path(output_file)
        self.metadata = metadata or {}
        self.scenario_time_source = scenario_time_source or (lambda: 0.0)
        self.logtime_source = logtime_source or time.time
        self.gaze_file_handle = None
        self._writer = None

    def start(self) -> Path:
        try:
            self._create_file(self.output_file)
        except PermissionError:
            print(f"Warning: Could not access {self.output_file}. File may be locked.")
            self.output_file = self.output_file.with_name(f"{self.output_file.stem}_{int(time.time())}.csv")
            self._create_file(self.output_file)

        self.my_eyetracker.subscribe_to(tr.EYETRACKER_GAZE_DATA, self.gaze_data_callback, as_dictionary=True)
        print(f"[OK] Eye tracking started. Saving to: {self.output_file}")
        return self.output_file

    def _create_file(self, output_file: Path) -> None:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with output_file.open('w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'participant_id',
                'session_id',
                'scenario_name',
                'matb_session_file',
                'matb_logtime',
                'scenario_time',
                'tobii_system_time_stamp',
                'GazePointLeft_X',
                'GazePointLeft_Y',
                'GazePointRight_X',
                'GazePointRight_Y',
                'GazePointAvg_X',
                'GazePointAvg_Y',
            ])

    def gaze_data_callback(self, gaze_data):
        try:
            if self.gaze_file_handle is None:
                self.gaze_file_handle = self.output_file.open('a', newline='')
                self._writer = csv.writer(self.gaze_file_handle)

            left_point = gaze_data.get('left_gaze_point_on_display_area')
            right_point = gaze_data.get('right_gaze_point_on_display_area')

            if left_point and right_point and self._writer is not None:
                avg_x = (left_point[0] + right_point[0]) / 2
                avg_y = (left_point[1] + right_point[1]) / 2
                self._writer.writerow([
                    self.metadata.get("participant_id", ""),
                    self.metadata.get("session_id", ""),
                    self.metadata.get("scenario_name", ""),
                    self.metadata.get("matb_session_file", ""),
                    self.logtime_source(),
                    self.scenario_time_source(),
                    gaze_data.get('system_time_stamp', ''),
                    left_point[0],
                    left_point[1],
                    right_point[0],
                    right_point[1],
                    avg_x,
                    avg_y,
                ])
                self.gaze_file_handle.flush()
        except Exception as e:
            print(f"Error writing gaze data: {e}")

    def stop(self) -> None:
        self.my_eyetracker.unsubscribe_from(tr.EYETRACKER_GAZE_DATA, self.gaze_data_callback)
        if self.gaze_file_handle:
            self.gaze_file_handle.close()
            self.gaze_file_handle = None
        print(f"[OK] Eye tracking stopped. Data saved to: {self.output_file}")


def calibrate_validate_and_start_recording(
    output_file: str | Path = "tobii_gaze_data.csv",
    metadata: dict[str, Any] | None = None,
    scenario_time_source: Callable[[], float] | None = None,
    logtime_source: Callable[[], float] | None = None,
) -> GazeRecorder:
    my_eyetracker = run_calibration_validation()
    recorder = GazeRecorder(my_eyetracker, output_file, metadata, scenario_time_source, logtime_source)
    recorder.start()
    return recorder


if __name__ == "__main__":
    recorder = calibrate_validate_and_start_recording()
    print("Recording for 30 seconds... Press Ctrl+C to stop early.")
    try:
        time.sleep(30)
    except KeyboardInterrupt:
        print("\n\nRecording interrupted by user.")
    finally:
        recorder.stop()
