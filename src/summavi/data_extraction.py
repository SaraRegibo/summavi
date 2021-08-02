from enum import Enum

import numpy as np
from fitdecode import FitReader
from fitdecode.records import FitDataMessage

ANGLE_CONVERSION = 2.**32 / 360.


def angular_coordinate_to_degrees(angular_coordinates):
    """ Convert the given angular coordinate(s) from a FIT file to degrees.

    Garmin stores its angular coordinates using a 32-bit integer (which gives 2**32 possible values).  These
    represent values up to 360° (or between -180° and 180°).

    Args:
        - angular_coordinates: Angular coordinate(s) as stored in a FIT file (as a 32-bit integer).

    Returns: Angular coordinates [degrees].
    """

    return angular_coordinates / ANGLE_CONVERSION


class DataType(str, Enum):
    """ Enumeration of the data types.

    Possible values are:

        - TIME, to extract time as datetime objects;
        - LATITUDE, to extract the latitude, as a 32-bit integer;
        - LONGITUDE, to extract the longitude, as a 32-bit integer
        - POWER, to extract the power [W];
        - HEART_RATE, to extract the heart rate [bpm];
        - CADENCE, to extract the cadence [rpm];
        - GROUND_TIME, to extract the ground contact time [ms];
        - VERTICAL_OSCILLATION, to extract the vertical oscillation [cm];
        - AIR_POWER, to extract the air power [%];
        - FORM_POWER, to extract the form power [W];
        - LEG_SPRING_STIFFNESS, to extrac the leg spring stiffness [kN/m].
    """

    TIME = "timestamp"
    LATITUDE = "position_lat"
    LONGITUDE = "position_long"
    POWER = "Power"
    HEART_RATE = "heart_rate"
    CADENCE = "Cadence"
    GROUND_TIME = "Ground Time"
    VERTICAL_OSCILLATION = "Vertical Oscillation"
    AIR_POWER = "Air Power"
    FORM_POWER = "Form Power"
    LEG_SPRING_STIFFNESS = "Leg Spring Stiffness"


def get_latitude(fit_filename: str):
    """ Extract the latitude values from the FIT file with the given filename.

    Args:
        - fit_filename: Filename of the FIT file from which to extract the latitude.

    Returns:
        - Numpy array with the timestamps from the FIT file with the given filename.
        - Numpy array with the latitude from the FIT file with the given filename [degrees].
    """

    time, latitude = get_data(fit_filename, DataType.LATITUDE)

    return time, angular_coordinate_to_degrees(latitude)


def get_longitude(fit_filename: str):
    """ Extract the longitude values from the FIT file with the given filename.

    Args:
        - fit_filename: Filename of the FIT file from which to extract the longitude.

    Returns:
        - Numpy array with the timestamps from the FIT file with the given filename.
        - Numpy array with the longitude from the FIT file with the given filename [degrees].
    """

    time, longitude = get_data(fit_filename, DataType.LONGITUDE)

    return time, angular_coordinate_to_degrees(longitude)


def get_power(fit_filename: str):
    """ Extract the power values from the FIT file with the given filename.

    Args:
        - fit_filename: Filename of the FIT file from which to extract the power.

    Returns:
        - Numpy array with the timestamps from the FIT file with the given filename.
        - Numpy array with the power from the FIT file with the given filename [W].
    """

    return get_data(fit_filename, DataType.POWER)


def get_heart_rate(fit_filename: str):
    """ Extract the heart rate values from the FIT file with the given filename.

    Args:
        - fit_filename: Filename of the FIT file from which to extract the heart rate.

    Returns:
        - Numpy array with the timestamps from the FIT file with the given filename.
        - Numpy array with the heart rate from the FIT file with the given filename [bpm].
    """

    return get_data(fit_filename, DataType.HEART_RATE)


def get_cadence(fit_filename: str):
    """ Extract the cadence values from the FIT file with the given filename.

    Whereas the cadence is expressed in rpm (revolutions per minute) in the FIT file, the returned cadence will be
    expressed in spm (steps per minute).

    Args:
        - fit_filename: Filename of the FIT file from which to extract the cadence.

    Returns:
        - Numpy array with the timestamps from the FIT file with the given filename.
        - Numpy array with the cadence from the FIT file with the given filename [spm].
    """
    time, cadence = get_data(fit_filename, DataType.CADENCE)

    return time, 2 * cadence


def get_ground_contact_time(fit_filename):
    """ Extract the ground contact time values from the FIT file with the given filename.

    Args:
        - fit_filename: Filename of the FIT file from which to extract the ground contact time.

    Returns:
        - Numpy array with the timestamps from the FIT file with the given filename.
        - Numpy array with the ground contact time from the FIT file with the given filename [ms].
    """
    return get_data(fit_filename, DataType.GROUND_TIME)


def get_vertical_oscillation(fit_filename: str):
    """ Extract the vertical oscillation values from the FIT file with the given filename.

    Args:
        - fit_filename: Filename of the FIT file from which to extract the vertical oscillation.

    Returns:
        - Numpy array with the timestamps from the FIT file with the given filename.
        - Numpy array with the vertical oscillation from the FIT file with the given filename [cm].
    """
    return get_data(fit_filename, DataType.VERTICAL_OSCILLATION)


def get_air_power(fit_filename: str):
    """ Extract the air power values from the FIT file with the given filename.

    The air power is the power that is needed to overcome air resistence.

    Args:
        - fit_filename: Filename of the FIT file from which to extract the air power.

    Returns:
        - Numpy array with the timestamps from the FIT file with the given filename.
        - Numpy array with the air power from the FIT file with the given filename [%].
    """
    return get_data(fit_filename, DataType.AIR_POWER)


def get_form_power(fit_filename: str):
    """ Extract the form power values from the FIT file with the given filename.

    Form power is essentially your "running in place" power.

    Args:
        - fit_filename: Filename of the FIT file from which to extract the form power.

    Returns:
        - Numpy array with the timestamps from the FIT file with the given filename.
        - Numpy array with the form power from the FIT file with the given filename [W].
    """
    return get_data(fit_filename, DataType.FORM_POWER)


def get_leg_spring_stiffness(fit_filename: str):
    """ Extract the leg spring stiffness values from the FIT file with the given filename.

    Leg spring stiffness is a measure how well a runner recycles the energy applied to the ground. This metric measures
    the stiffness of the muscles and tendons in your legs.

    Args:
        - fit_filename: Filename of the FIT file from which to extract the leg spring stiffness.

    Returns:
        - Numpy array with the timestamps from the FIT file with the given filename.
        - Numpy array with the leg spring stiffness from the FIT file with the given filename [kN/m].
    """

    return get_data(fit_filename, DataType.LEG_SPRING_STIFFNESS)


def get_data(fit_filename: str, data_type: DataType):
    """ Extract the values from the FIT file with the given filename for the given data type.

    Args:
        - fit_filename: Filename of the FIT file from which to extract the data.
        - data_type: Name of the parameter for which to extract the data.

    Returns:
        - Numpy array with the timestamps from the FIT file with the given filename.
        - Numpy array with the values from the FIT file with the given filename for the given data type.
    """

    time = np.array([])
    data = np.array([])

    time0 = None

    with FitReader(fit_filename) as fit_file:

        for frame in fit_file:

            if isinstance(frame, FitDataMessage):

                if frame.name == "record":

                    if frame.has_field(data_type):

                        timepoint = frame.get_value(DataType.TIME)
                        value = frame.get_value(data_type)

                        if value is not None:

                            print(f"Value: {value}")
                            data = np.append(data, float(value))

                            if time0 is None:

                                time0 = frame.get_value(DataType.TIME)

                            time = np.append(time, (timepoint - time0).total_seconds())

    return time, data
