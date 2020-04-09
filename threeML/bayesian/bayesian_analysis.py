from __future__ import print_function
from __future__ import division
from builtins import range
from builtins import object
from past.utils import old_div
import emcee
import emcee.utils


try:

    import chainconsumer

except:

    has_chainconsumer = False

else:

    has_chainconsumer = True

try:

    # see if we have mpi and/or are using parallel

    from mpi4py import MPI
    if MPI.COMM_WORLD.Get_size() > 1: # need parallel capabilities
        using_mpi = True

        comm = MPI.COMM_WORLD
        rank = comm.Get_rank()

    else:

        using_mpi = False
except:

    using_mpi = False








import numpy as np
import collections
import math
import os
import time

import matplotlib.pyplot as plt

from threeML.parallel.parallel_client import ParallelClient
from threeML.config.config import threeML_config
from threeML.io.progress_bar import progress_bar
from threeML.exceptions.custom_exceptions import LikelihoodIsInfinite, custom_warnings
from threeML.analysis_results import BayesianResults
from threeML.utils.statistics.stats_tools import aic, bic, dic
from threeML.bayesian.sampler import Sampler


from astromodels import ModelAssertionViolation, use_astromodels_memoization


class BayesianAnalysis(object):
    def __init__(self, likelihood_model, data_list, **kwargs):
        """
        Bayesian analysis.

        :param likelihood_model: the likelihood model
        :param data_list: the list of datasets to use (normally an instance of DataList)
        :param kwargs: use 'verbose=True' for verbose operation
        :return:
        """

        self._analysis_type = "bayesian"



        self._likelihood_model = likelihood_model
        self._data_list = data_list
        
        # # Make sure that the current model is used in all data sets
        #
        # for dataset in self.data_list.values():
        #     dataset.set_model(self._likelihood_model)

        # Init the samples to None

        self._samples = None
        self._raw_samples = None
        self._sampler = None
        self._log_like_values = None
        self._results = None

        # Get the initial list of free parameters, useful for debugging purposes


    def set_sampler(self, sampler):

        assert isinstance(sampler, Sampler)

        self._sampler = sampler
        self._sampler.register(self._likelihood_model, self._data_list)
        
    @property
    def sampler(self):

        return self._sampler


    def sample(self,quiet=False):
        self._sampler.sample(quiet=quiet)

        # attach everything locally
        
        self._results = self._sampler.sampler.results
        self._samples = self._sampler.sampler.samples
        self._raw_samples = self._sampler.sampler.raw_samples
        self._log_like_values = self._sampler.sampler.log_like_values
        self._results = self._sampler.sampler.results
        
    @property
    def results(self):

        return self._results

    @property
    def analysis_type(self):
        return self._analysis_type

    @property
    def log_like_values(self):
        """
        Returns the value of the log_likelihood found by the bayesian sampler while sampling from the posterior. If
        you need to find the values of the parameters which generated a given value of the log. likelihood, remember
        that the samples accessible through the property .raw_samples are ordered in the same way as the vector
        returned by this method.

        :return: a vector of log. like values
        """
        return self._log_like_values

    @property
    def log_probability_values(self):
        """
        Returns the value of the log_probability (posterior) found by the bayesian sampler while sampling from the posterior. If
        you need to find the values of the parameters which generated a given value of the log. likelihood, remember
        that the samples accessible through the property .raw_samples are ordered in the same way as the vector
        returned by this method.

        :return: a vector of log probabilty values
        """

        return self._log_probability_values

    @property
    def log_marginal_likelihood(self):
        """
        Return the log marginal likelihood (evidence) if computed
        :return:
        """

        return self._marginal_likelihood


    def sample_parallel_tempering(self, n_temps, n_walkers, burn_in, n_samples, quiet=False):
        """
        Sample with parallel tempering

        :param: n_temps
        :param: n_walkers
        :param: burn_in
        :param: n_samples

        :return: MCMC samples

        """

        free_parameters = self._likelihood_model.free_parameters

        n_dim = len(list(free_parameters.keys()))

        sampler = emcee.PTSampler(n_temps, n_walkers, n_dim, self._log_like, self._log_prior)

        # Get one starting point for each temperature

        p0 = np.empty((n_temps, n_walkers, n_dim))

        for i in range(n_temps):
            p0[i, :, :] = self._get_starting_points(n_walkers)

        print("Running burn-in of %s samples...\n" % burn_in)

        p, lnprob, lnlike = sample_with_progress("Burn-in", p0, sampler, burn_in)

        # Reset sampler

        sampler.reset()

        print("\nSampling\n")

        _ = sample_with_progress("Sampling", p, sampler, n_samples,
                                 lnprob0=lnprob, lnlike0=lnlike)

        self._sampler = sampler

        # Now build the _samples dictionary

        self._raw_samples = sampler.get_chain(flat=True).reshape(-1,
            sampler.get_chain(flat=True).shape[-1])

        self._log_probability_values = None

        self._log_like_values = None

        self._marginal_likelihood = None

        self._build_samples_dictionary()

        self._build_results()

        # Display results
        if not quiet:
            self._results.display()

        return self.samples




    @property
    def raw_samples(self):
        """
        Access the samples from the posterior distribution generated by the selected sampler in raw form (i.e.,
        in the format returned by the sampler)

        :return: the samples as returned by the sampler
        """

        return self._raw_samples

    @property
    def samples(self):
        """
        Access the samples from the posterior distribution generated by the selected sampler

        :return: a dictionary with the samples from the posterior distribution for each parameter
        """
        return self._samples

    @property
    def sampler(self):
        """
        Access the instance of the sampler used to sample the posterior distribution
        :return: an instance of the sampler
        """

        return self._sampler


    def plot_chains(self, thin=None):
        """
        Produce a plot of the series of samples for each parameter

        :parameter thin: use only one sample every 'thin' samples
        :return: a matplotlib.figure instance
        """

        return self._results.plot_chains( thin )

    @property
    def likelihood_model(self):
        """
        :return: likelihood model (a Model instance)
        """
        return self._likelihood_model

    @property
    def data_list(self):
        """
        :return: data list for this analysis
        """

        return self._data_list

    def convergence_plots(self, n_samples_in_each_subset, n_subsets):
        """
        Compute the mean and variance for subsets of the samples, and plot them. They should all be around the same
        values if the MCMC has converged to the posterior distribution.

        The subsamples are taken with two different strategies: the first is to slide a fixed-size window, the second
        is to take random samples from the chain (bootstrap)

        :param n_samples_in_each_subset: number of samples in each subset
        :param n_subsets: number of subsets to take for each strategy
        :return: a matplotlib.figure instance
        """

        return self._results.convergence_plots( n_samples_in_each_subset, n_subsets)
        

    def restore_median_fit(self):
        """
        Sets the model parameters to the mean of the marginal distributions
        """

        for i, (parameter_name, parameter) in enumerate(self._free_parameters.items()):
            # Add the samples for this parameter for this source

            mean_par = np.median(self._samples[parameter_name])
            parameter.value = mean_par


    @staticmethod
    def _calc_min_interval(x, alpha):
        """
        Internal method to determine the minimum interval of a given width
        Assumes that x is sorted numpy array.
        :param a: a numpy array containing samples
        :param alpha: probability of type I error

        :returns: list containing min and max HDI

        """

        n = len(x)
        cred_mass = 1.0 - alpha

        interval_idx_inc = int(np.floor(cred_mass * n))
        n_intervals = n - interval_idx_inc
        interval_width = x[interval_idx_inc:] - x[:n_intervals]

        if len(interval_width) == 0:
            raise ValueError('Too few elements for interval calculation')

        min_idx = np.argmin(interval_width)
        hdi_min = x[min_idx]
        hdi_max = x[min_idx + interval_idx_inc]
        return hdi_min, hdi_max

    def _hpd(self, x, alpha=0.05):
        """Calculate highest posterior density (HPD) of array for given alpha.
        The HPD is the minimum width Bayesian credible interval (BCI).

        :param x: array containing MCMC samples
        :param alpha : Desired probability of type I error (defaults to 0.05)
        """
        sx = np.sort(x)
        return np.array(self._calc_min_interval(sx, alpha))
