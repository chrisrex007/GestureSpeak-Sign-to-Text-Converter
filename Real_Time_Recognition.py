import streamlit as st
st.set_page_config(page_title="ASL Recognition", page_icon="🤟", layout="centered")
import pickle
import cv2
import mediapipe as mp
import numpy as np
import time

# Sidebar title
st.sidebar.title("📌 Navigation Menu")

def calculate_angle(v1, v2):
    """Calculate the angle between two vectors."""
    v1 = np.array(v1)
    v2 = np.array(v2)
    cosine_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
    angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0))
    return np.degrees(angle)

# Load the main model
with open('models/model_main.p', 'rb') as f:
    model_dict = pickle.load(f)

model = model_dict['model']

# Constants
offset = 20

# Mediapipe Hands setup
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.6)

# Label dictionary for predictions
labels_dict = {
    0:'space', 1: 'A', 2: 'B', 3: 'C', 4: 'D', 5: 'E', 6: 'F', 7: 'G', 8: 'H', 9: 'I', 10: 'J',
    11: 'K', 12: 'L', 13: 'M', 14: 'N', 15: 'O', 16: 'P', 17: 'Q', 18: 'R', 19: 'S',
    20: 'T', 21: 'U', 22: 'V', 23: 'W', 24: 'X', 25: 'Y', 26: 'Z', 27: 'delete'
}

# Streamlit UI setup
st.title("GestureSpeak: ASL Hand Gesture Recognition")
st.write("Show an ASL hand sign to recognize it. Press **Stop Webcam** to quit.")

# Webcam state initialization
if "run_webcam" not in st.session_state:
    st.session_state.run_webcam = False

# Button Controls for webcam
col1, col2 = st.columns(2)
with col1:
    if st.button("Start Webcam"):
        st.session_state.run_webcam = True
with col2:
    if st.button("Stop Webcam"):
        st.session_state.run_webcam = False

# Placeholders for video and output
stframe = st.empty()
prediction_text = st.empty()
result_text = st.empty()

# Track previous prediction and time for stability
previous_prediction = None
start_time = None

# Initialize recognized text
if "recognized_text" not in st.session_state:
    st.session_state.recognized_text = ""   

# Main webcam loop
if st.session_state.run_webcam:
    cap = cv2.VideoCapture(0)

    while st.session_state.run_webcam:
        ret, frame = cap.read()
        if not ret:
            st.error("Failed to capture image.")
            break

        imgRGB = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(imgRGB)

        predicted_character = "None"

        if results.multi_hand_landmarks:
            hand_landmarks = results.multi_hand_landmarks[0]
            h, w, _ = frame.shape
            x_min, y_min, x_max, y_max = w, h, 0, 0

            # Find bounding box for the hand
            for landmark in hand_landmarks.landmark:
                x, y = int(landmark.x * w), int(landmark.y * h)
                x_min, y_min = min(x_min, x), min(y_min, y)
                x_max, y_max = max(x_max, x), max(y_max, y)

            x_min, y_min = max(0, x_min - offset), max(0, y_min - offset)
            x_max, y_max = min(w, x_max + offset), min(h, y_max + offset)

            data_aux = []
            x_, y_, z_ = [], [], []
            landmarks = []

            # Collect landmark coordinates
            for i in range(21):
                x = hand_landmarks.landmark[i].x
                y = hand_landmarks.landmark[i].y
                z = hand_landmarks.landmark[i].z

                x_.append(x)
                y_.append(y)
                z_.append(z)
                landmarks.append((x, y, z))

            min_x, min_y, min_z = min(x_), min(y_), min(z_)
            for i in range(21):
                data_aux.append(x_[i]/min_x)
                data_aux.append(y_[i]/ min_y)
                data_aux.append(z_[i]/ min_z)

            # Add finger joint angles as features
            finger_joints = [(4, 1, 8, 5), (8, 5, 12, 9), (12, 9, 16, 13), (16, 13, 20, 17)]
            for joint in finger_joints:
                v1 = np.subtract(landmarks[joint[0]], landmarks[joint[1]])
                v2 = np.subtract(landmarks[joint[2]], landmarks[joint[3]])
                data_aux.append(calculate_angle(v1, v2))

            data_aux = np.array(data_aux).reshape(1, -1)

            # Predict only with the main model (specialized models removed)
            if data_aux.shape[1] == 67:
                prediction = model.predict(data_aux)
                predicted_index = int(prediction[0])
                predicted_character = labels_dict[predicted_index]

                # Track and print if character is stable for 2 seconds
                if predicted_character == previous_prediction:
                    if time.time() - start_time >= 2:
                        if(predicted_character == 'space'):
                            st.session_state.recognized_text+=' '
                        else:
                            if(predicted_character == 'delete'):
                                st.session_state.recognized_text = st.session_state.recognized_text[:-1]
                            else:
                                st.session_state.recognized_text += predicted_character
                        cv2.putText(frame, predicted_character + ' is detected', (300, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 255, 0), 3, cv2.LINE_AA)
                        previous_prediction = None
                else:
                    previous_prediction = predicted_character
                    start_time = time.time()
            else:
                print("Incorrect number of features")

            # Draw bounding box and prediction on frame
            cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (0, 0, 0), 2)
            cv2.putText(frame, predicted_character, (x_min, y_min - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 255, 0), 3, cv2.LINE_AA)

        # Display video and predictions in Streamlit
        stframe.image(frame, channels="BGR")
        prediction_text.subheader(f"Predicted Character: **{predicted_character}**")
        result_text.subheader(f"Recognized Text: **{st.session_state.recognized_text}**")

    cap.release()
    cv2.destroyAllWindows()
# Display final recognized text after webcam stops
if not st.session_state.run_webcam:
    st.subheader(f"Final Recognized Text: **{st.session_state.recognized_text}**")
