import numpy as np
import numexpr

from threeML.utils.stats_tools import Significance
from threeML.io.progress_bar import progress_bar


class NotEnoughData(RuntimeError):
    pass


class Rebinner(object):
    """
    A class to rebin vectors keeping a minimum value per bin. It supports array with a mask, so that elements excluded
    through the mask will not be considered for the rebinning

    """

    def __init__(self, vector_to_rebin_on, min_value_per_bin, mask=None):

        # Basic check that it is possible to do what we have been requested to do

        total = np.sum(vector_to_rebin_on)

        if total < min_value_per_bin:
            raise NotEnoughData("Vector total is %s, cannot rebin at %s per bin" % (total, min_value_per_bin))

        # Check if we have a mask, if not prepare a empty one
        if mask is not None:

            mask = np.array(mask, bool)

            assert mask.shape[0] == len(vector_to_rebin_on), "The provided mask must have the same number of " \
                                                             "elements as the vector to rebin on"

        else:

            mask = np.ones_like(vector_to_rebin_on, dtype=bool)

        self._mask = mask

        # Rebin taking the mask into account

        self._starts = []
        self._stops = []
        self._grouping = np.zeros_like(vector_to_rebin_on)

        n = 0
        bin_open = False

        n_grouped_bins = 0

        for index, b in enumerate(vector_to_rebin_on):

            if not mask[index]:

                # This element is excluded by the mask

                if not bin_open:

                    # Do nothing
                    continue

                else:

                    # We need to close the bin here
                    self._stops.append(index)
                    n = 0
                    bin_open = False

                    # If we have grouped more than one bin

                    if n_grouped_bins > 1:

                        # group all these bins
                        self._grouping[index - n_grouped_bins + 1: index] = -1
                        self._grouping[index] = 1

                    # reset the number of bins in this group

                    n_grouped_bins = 0

            else:

                # This element is included by the mask

                if not bin_open:
                    # Open a new bin
                    bin_open = True

                    self._starts.append(index)
                    n = 0

                # Add the current value to the open bin

                n += b

                n_grouped_bins += 1

                # If we are beyond the requested value, close the bin

                if n >= min_value_per_bin:
                    self._stops.append(index + 1)

                    n = 0

                    bin_open = False

                    # If we have grouped more than one bin

                    if n_grouped_bins > 1:

                        # group all these bins
                        self._grouping[index - n_grouped_bins + 1: index] = -1
                        self._grouping[index] = 1

                    # reset the number of bins in this group

                    n_grouped_bins = 0

        # At the end of the loop, see if we left a bin open, if we did, close it

        if bin_open:
            self._stops.append(len(vector_to_rebin_on))

        assert len(self._starts) == len(self._stops), "This is a bug: the starts and stops of the bins are not in " \
                                                      "equal number"

        self._min_value_per_bin = min_value_per_bin

    @property
    def n_bins(self):
        """
        Returns the number of bins defined.

        :return:
        """

        return len(self._starts)

    @property
    def grouping(self):

        return self._grouping

    def rebin(self, *vectors):

        rebinned_vectors = []

        for vector in vectors:

            assert len(vector) == len(self._mask), "The vector to rebin must have the same number of elements of the" \
                                                   "original (not-rebinned) vector"

            # Transform in array because we need to use the mask
            vector_a = np.array(vector)

            rebinned_vector = []

            for low_bound, hi_bound in zip(self._starts, self._stops):

                rebinned_vector.append(np.sum(vector_a[low_bound:hi_bound]))

            # Vector might not contain counts, so we use a relative comparison to check that we didn't miss
            # anything.
            # NOTE: we add 1e-100 because if both rebinned_vector and vector_a contains only 0, the check would
            # fail when it shouldn't

            assert abs((np.sum(rebinned_vector) + 1e-100) / (np.sum(vector_a[self._mask]) + 1e-100) - 1) < 1e-4

            rebinned_vectors.append(np.array(rebinned_vector))

        return rebinned_vectors

    def rebin_errors(self, *vectors):
        """
        Rebin errors by summing the squares

        Args:
            *vectors:

        Returns:
            array of rebinned errors

        """

        rebinned_vectors = []

        for vector in vectors:  # type: np.ndarray[np.ndarray]

            assert len(vector) == len(self._mask), "The vector to rebin must have the same number of elements of the" \
                                                   "original (not-rebinned) vector"

            rebinned_vector = []

            for low_bound, hi_bound in zip(self._starts, self._stops):

                rebinned_vector.append(np.sqrt(np.sum(vector[low_bound:hi_bound] ** 2)))

            rebinned_vectors.append(np.array(rebinned_vector))

        return rebinned_vectors

    def get_new_start_and_stop(self, old_start, old_stop):

        assert len(old_start) == len(self._mask) and len(old_stop) == len(self._mask)

        new_start = np.zeros(len(self._starts))
        new_stop = np.zeros(len(self._starts))

        for i, (low_bound, hi_bound) in enumerate(zip(self._starts, self._stops)):
            new_start[i] = old_start[low_bound]
            new_stop[i] = old_stop[hi_bound - 1]

        return new_start, new_stop

        # def save_active_measurements(self, mask):
        #     """
        #     Saves the set active measurements so that they can be restored if the binning is reset.
        #
        #
        #     Returns:
        #         none
        #
        #     """
        #
        #     self._saved_mask = mask
        #     self._saved_idx = np.array(slice_disjoint((mask).nonzero()[0])).T
        #
        # @property
        # def saved_mask(self):
        #
        #     return self._saved_mask
        #
        # @property
        # def saved_selection(self):
        #
        #     return self._saved_idx
        #
        # @property
        # def min_counts(self):
        #
        #     return self._min_value_per_bin
        #
        # @property
        # def edges(self):
        #
        #     # return the low and high bins
        #     return np.array(self._edges[:-1]) + 1, np.array(self._edges[1:])



class TemporalBinner(object):
    """
    A class to provide binning of temporal light curves via various methods

    """

    def __init__(self, arrival_times):

        self._arrival_times = arrival_times

    @property
    def bins(self):

        return [np.asarray(self._starts), np.asarray(self._stops)]

    @property
    def text_bins(self):

        txt_bins = []

        for start, stop in zip(self._starts, self._stops):

            txt_bins.append("%f-%f" % (start, stop))

        return txt_bins

    def bin_by_significance(self, background_getter, background_error_getter=None, sigma_level=10, min_counts=1):
        """

        Bin the data to a given significance level for a given background method and sigma
        method. If a background error function is given then it is assumed that the error distribution
        is gaussian. Otherwise, the error distribution is assumed to be Poisson.

        :param background_getter: function of a start and stop time that returns background counts
        :param background_error_getter: function of a start and stop time that returns background count errors
        :param sigma_level: the sigma level of the intervals
        :param min_counts: the minimum counts per bin

        :return:
        """

        self._starts = []

        self._stops = []

        total_counts = 0
        current_start = self._arrival_times[0]

        with progress_bar(len(self._arrival_times)) as p:
            for i, time in enumerate(self._arrival_times):

                total_counts += 1

                if total_counts < min_counts:

                    continue

                else:

                    # first use the background function to know the number of background counts
                    bkg = background_getter(current_start, time)

                    sig = Significance(total_counts, bkg)

                    if background_error_getter is not None:

                        bkg_error = background_error_getter(current_start, time)

                        sigma = sig.li_and_ma_equivalent_for_gaussian_background(bkg_error)[0]




                    else:

                        sigma = sig.li_and_ma()[0]

                    # now test if we have enough sigma



                    if sigma >= sigma_level:

                        self._stops.append(time)

                        self._starts.append(current_start)

                        current_start = time

                        total_counts = 0

                p.increase()

    def bin_by_constanst(self, dt):
        """
        Create bins with a constant dt

        :param dt: temporal spacing of the bins
        :return: None
        """

        tmp = np.arange(self._arrival_times[0], self._arrival_times[-1], dt)
        self._starts = tmp
        self._stops = tmp + dt

    def bin_by_bayesian_blocks(self, p0, bkg_integral_distribution=None, my_likelihood=None):
        """Divide a series of events characterized by their arrival time in blocks
        of perceptibly constant count rate. If the background integral distribution
        is given, divide the series in blocks where the difference with respect to
        the background is perceptibly constant.
        Args:
          self._arrival_times (iterable): An iterable (list, numpy.array...) containing the arrival
                         time of the events.
                         NOTE: the input array MUST be time-ordered, and without
                         duplicated entries. To ensure this, you may execute the
                         following code:
                         tt_array = numpy.asarray(self._arrival_times)
                         tt_array = numpy.unique(tt_array)
                         tt_array.sort()
                         before running the algorithm.
          p0 (float): The probability of finding a variations (i.e., creating a new
                      block) when there is none. In other words, the probability of
                      a Type I error, i.e., rejecting the null-hypothesis when is
                      true. All found variations will have a post-trial significance
                      larger than p0.
          bkg_integral_distribution (function, optional): the integral distribution for the
                      background counts. It must be a function of the form f(x),
                      which must return the integral number of counts expected from
                      the background component between time 0 and x.
        Returns:
          numpy.array: the edges of the blocks found
        """

        # Verify that the input array is one-dimensional



        t_start = self._arrival_times[0]
        t_stop = self._arrival_times[-1]

        if (bkg_integral_distribution is not None):
            # Transforming the inhomogeneous Poisson process into an homogeneous one with rate 1,
            # by changing the time axis according to the background rate

            t = np.array(bkg_integral_distribution(self._arrival_times))

            # Now compute the start and stop time in the new system
            tstart = bkg_integral_distribution(t_start)
            tstop = bkg_integral_distribution(t_stop)
        else:
            t = self._arrival_times
            tstart = t_start
            tstop = t_stop
        pass

        # Create initial cell edges (Voronoi tessellation)
        edges = np.concatenate([[tstart],
                                0.5 * (t[1:] + t[:-1]),
                                [tstop]])

        # Create the edges also in the original time system
        edges_ = np.concatenate([[t_start],
                                 0.5 * (self._arrival_times[1:] + self._arrival_times[:-1]),
                                 [t_stop]])

        # Create a lookup table to be able to transform back from the transformed system
        # to the original one
        lookup_table = {key: value for (key, value) in zip(edges, edges_)}

        # The last block length is 0 by definition
        block_length = tstop - edges

        if np.sum((block_length <= 0)) > 1:

            raise RuntimeError("Events appears to be out of order! Check for order, or duplicated events.")

        N = t.shape[0]

        # arrays to store the best configuration
        best = np.zeros(N, dtype=float)
        last = np.zeros(N, dtype=int)
        best_new = np.zeros(N, dtype=float)
        last_new = np.zeros(N, dtype=int)

        # Pre-computed priors (for speed)

        if my_likelihood:

            priors = my_likelihood.getPriors(N, p0)

        else:

            # eq. 21 from Scargle 2012
            priors = 4 - np.log(73.53 * p0 * np.power(np.arange(1, N + 1), -0.478))
        pass

        x = np.ones(N)

        # Speed tricks: resolve once for all the functions which will be used
        # in the loop
        cumsum = np.cumsum
        log = np.log
        argmax = np.argmax
        numexpr_evaluate = numexpr.evaluate
        arange = np.arange

        # Decide the step for reporting progress
        # incr = max(int(float(N) / 100.0 * 10), 1)


        # This is where the computation happens. Following Scargle et al. 2012.
        # This loop has been optimized for speed:
        # * the expression for the fitness function has been rewritten to
        #  avoid multiple log computations, and to avoid power computations
        # * the use of scipy.weave and numexpr has been evaluated. The latter
        #  gives a big gain (~40%) if used for the fitness function. No other
        #  gain is obtained by using it anywhere else

        times = []
        TSs = []

        # Set numexpr precision to low (more than enough for us), which is
        # faster than high
        old_accuracy = numexpr.set_vml_accuracy_mode('low')
        numexpr.set_num_threads(1)
        numexpr.set_vml_num_threads(1)

        with progress_bar(N) as prg:
            for R in range(N):

                br = block_length[R + 1]
                T_k = block_length[:R + 1] - br

                # N_k: number of elements in each block
                # This expression has been simplified for the case of
                # unbinned events (i.e., one element in each block)
                # It was:
                # N_k = cumsum(x[:R + 1][::-1])[::-1]
                # Now it is:
                N_k = arange(R + 1, 0, -1)

                # Evaluate fitness function
                # This is the slowest part, which I'm speeding up by using
                # numexpr. It provides a ~40% gain in execution speed.

                fit_vec = numexpr_evaluate('''N_k * log(N_k/ T_k) ''',
                                           optimization='aggressive')

                p = priors[R]

                A_R = fit_vec - p

                A_R[1:] += best[:R]

                i_max = argmax(A_R)

                last[R] = i_max
                best[R] = A_R[i_max]

                prg.increase()

        numexpr.set_vml_accuracy_mode(old_accuracy)

        # Now find blocks
        change_points = np.zeros(N, dtype=int)
        i_cp = N
        ind = N
        while True:
            i_cp -= 1
            change_points[i_cp] = ind

            if ind == 0:
                break

            ind = last[ind - 1]

        change_points = change_points[i_cp:]

        edg = edges[change_points]

        # Transform the found edges back into the original time system
        if bkg_integral_distribution is not None:
            final_edges = map(lambda x: lookup_table[x], edg)
        else:
            final_edges = edg

        self._starts = np.asarray(final_edges)[:-1]
        self._stops = np.asarray(final_edges)[1:]

        # return np.asarray(finalEdges)




    def bin_by_custom(self, start, stop):
        """
        Simplicity function to make custom bins. This form keeps introduction of
        custom bins uniform for other binning methods

        :param start: start times of the bins
        :param stop:  stop times of the bins
        :return:
        """

        self._starts = start
        self._stops = stop
