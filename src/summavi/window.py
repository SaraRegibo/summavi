import numpy as np


def moving_window(time, signal, window_length, time_step, function, time0=None, pass_time_in_window=True, **kwargs):
    """ Apply the given function over a sliding window of the given length an return list of the function outputs.

    The boundaries of window n are:

        - start: time0 + n * time_step
        - end: time0 + n * time_step + window_length

    Windows that don't contain any data will be skipped.

    Args:
        - time: Time points in the time series.
        - signal: Metrics points of the time series.
        - window_length: Length of the windows, in the same unit as the given time points.
        - function: Function that will be applied to each window, with the signature:
                     - function(timeInWindow, signalInWindow)     by default.
                     - function(signalInWindow)                   if pass_time_in_window == False.
        - time0: Starting time of the first window, in the same unit as the given time points.  If None, time0 will be
                 set to time[0].
        - pass_time_in_window: Specifies if the given functions needs the time points in the window.
        - kwargs: Additional keyword arguments to pass to the given function.

    Returns: As the number of windows to which the function should be applied may be large, and because the function
             output may also be large, the function is a generator. So it does not pass all results one by one, but
             returns an iterator that gives the following tuple:

                - window_begin_time: time0 + n * time_step, with n=0,1,2,... of the generator.
                - windowEndTime: time0 + n * time_step + window_length, with n=0,1,2,... of the generator.
                - window_begin_index: Data contained in a window goes from time[window_begin_index] to
                                      time[window_end_index].  Because of gaps in the time series,
                                      time[window_end_index] - time[window_begin_index] < window_length.
                - window_end_index: See above.
                - function_output: Whatever function() returned as output for the current window.
    """

    if time0 is None:

        time0 = time[0]

    # Fast-forward, until the window covers at least one point of the time series

    window_begin_time = time0
    window_end_time = window_begin_time + window_length

    while window_end_time < time[0]:

        window_begin_time += time_step
        window_end_time += time_step

    # Loop over the entire time span of the time series, in steps of 'timeStep'.
    # The window length is fixed to 'windowLength', but the number of time points
    # in each window may vary because of gaps.

    stop_moving_window = False
    function_output = None

    while not stop_moving_window:

        window_indices = np.where((time >= window_begin_time) & (time < window_end_time))[0]

        if len(window_indices) != 0:

            window_begin_index = window_indices[0]
            window_end_index = window_indices[-1]

            try:

                if pass_time_in_window:

                    function_output = function(time[:window_end_index], signal[:window_end_index], **kwargs)

                else:

                    function_output = function(signal[:window_end_index], **kwargs)
            except:

                function_output = None

            yield window_begin_time, window_end_time, window_begin_index, window_end_index, function_output

        # If the window covers passed the last time point, then stop the moving window generator,
        # else move the entire window one time step

        if window_end_time < time[-1]:

            window_begin_time += time_step
            window_end_time += time_step

        else:

            stop_moving_window = True
