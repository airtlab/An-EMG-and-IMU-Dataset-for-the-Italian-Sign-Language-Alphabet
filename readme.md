
# An EMG and IMU Dataset for the Italian Sign Language Alphabet 

This repository contains surface EMG and IMU data collected with the Myo Gesture Control Armband about the gestures of the 26 letter of the Italian Sign Language Alphabet.

## Data Description

The dataset contains 780 gesture samples (30 for each letter of the alphabet) and is organized into 26 directories, one for each letter of the alphabet. Each directory includes 30 json file, one for each sample of the gesture representing a letter. Each json file is named using a Global Unique Identifier (GUID) and is organized as a json object as follows

	     JSON
 	     ├─ timestamp (string)
	     ├─ duration (integer)
	     ├─ emg (object)
	     │   ├─ frequency (integer)
	     │   └─ data (integer matrix, dimensions: 400 x 8)
	     └─ imu (object)
	         ├─ frequency (integer)
	         └─ data (object array, length: 400)
	             ├─ gyroscope (floating point array, length: 3)
	             ├─ acceleration (floating point array, length: 3)
	             └─ orientation (floating point array, length: 4)

The following fields are available:
-  *timestamp*, a string representing the date and time of the gesture acquisition. For example, the string “09/07/20/10:03:19” indicates that the gesture and its acquisition were performed the 9th of July 2020, at 10:03:19 a.m.
-  *duration*, an integer describing how long was the data acquisition of the gesture in milliseconds. The value is 2000 in all the json files, as the time window for the data acquisition was 2 seconds;
-  *emg*, an object representing the EMG data of the gesture. It has two fields
    -  *frequency*, i.e. the sampling frequency (in Hz) of the values from the EMG sensors. This value is 200 in all the json files;
    -  *data*, a 400 x 8 integer matrix. Each row is then an 8-dimensional array including the values from the 8 EMG sensors of the Myo Armband. Therefore, data is the time series of the values from the EMG sensors during the acquisition of the gesture;
-  *imu*, an object representing the IMU data of the gesture acquisition. It has two fields
    -  *frequency*, i.e. the sampling frequency (in Hz) of the values from the IMU. This value is 200 in all the json files;
    -  *data*, a 400 elements length object array. Each object has three fields, namely *gyroscope* (an array composed by 3 floating point values), *acceleration* (an array composed by 3 floating point values), and *rotation* (an array composed by 4 floating point values).

## Data Acquisition Script

## Dataset Release Agreement

The dataset is freely released for research and educational purposes.