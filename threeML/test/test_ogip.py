import pytest
import numpy as np
import os

__author__ = 'drjfunk'

from threeML.plugins.OGIPLike import OGIPLike
from threeML.plugins.OGIP.pha import PHA
from threeML.classicMLE.joint_likelihood import JointLikelihood
from threeML.plugins.OGIP.response import Response
from threeML.data_list import DataList
from threeML.classicMLE.likelihood_ratio_test import LikelihoodRatioTest
from astromodels.model import Model
from astromodels.functions.functions import Powerlaw, Exponential_cutoff, Cutoff_powerlaw
from astromodels.sources.point_source import PointSource



from threeML.io.file_utils import within_directory


__this_dir__ = os.path.join(os.path.abspath(os.path.dirname(__file__)))


class AnalysisBuilder(object):
    def __init__(self, plugin):

        self._plugin = plugin

        self._shapes = {}
        self._shapes['normal'] = Powerlaw()
        self._shapes['cpl'] = Cutoff_powerlaw()
        self._shapes['add'] = Powerlaw() + Cutoff_powerlaw
        self._shapes['mult'] = Powerlaw() * Exponential_cutoff()
        self._shapes['crazy'] = Exponential_cutoff() * (Powerlaw() + Powerlaw())

    @property
    def keys(self):

        return self._shapes.keys()

    def build_point_source_jl(self):

        data_list = DataList(self._plugin)

        jls = {}

        for key in self._shapes.keys():
            ps = PointSource('test', 0, 0, spectral_shape=self._shapes[key])
            model = Model(ps)
            jls[key] = JointLikelihood(model, data_list)

        return jls

    def build_point_source_bayes(self):

        data_list = DataList(self._plugin)

        jls = {}

        for key in self._shapes.keys():
            ps = PointSource('test', 0, 0, spectral_shape=self._shapes[key])
            model = Model(ps)
            jls[key] = JointLikelihood(model, data_list)

        return jls




def test_loading_a_generic_pha_file():
    with within_directory(__this_dir__):
        ogip = OGIPLike('test_ogip', pha_file='test.pha{1}')

        pha_info = ogip.get_pha_files()

        assert ogip.name == 'test_ogip'
        assert ogip.n_data_points == sum(ogip._mask)
        assert sum(ogip._mask) == ogip.n_data_points
        assert ogip.tstart is None
        assert ogip.tstop is None
        assert 'cons_test_ogip' in ogip.nuisance_parameters
        assert ogip.nuisance_parameters['cons_test_ogip'].fix == True
        assert ogip.nuisance_parameters['cons_test_ogip'].free == False

        assert 'pha' in pha_info
        assert 'bak' in pha_info
        assert 'rsp' in pha_info


def test_pha_files_in_generic_ogip_constructor_spec_number_in_file_name():
    with within_directory(__this_dir__):

        ogip = OGIPLike('test_ogip', pha_file='test.pha{1}')
        ogip.set_active_measurements('all')
        pha_info = ogip.get_pha_files()

        for key in ['pha', 'bak']:

            assert isinstance(pha_info[key], PHA)

        assert pha_info['pha'].background_file == 'test_bak.pha{1}'
        assert pha_info['pha'].ancillary_file == 'NONE'
        assert pha_info['pha'].instrument == 'GBM_NAI_03'
        assert pha_info['pha'].mission == 'GLAST'
        assert pha_info['pha'].is_poisson() == True
        assert pha_info['pha'].n_channels == ogip.n_data_points
        assert pha_info['pha'].n_channels == len(pha_info['pha'].rates)

        # Test that Poisson rates cannot call rate error
        with pytest.raises(AssertionError):

            _ = pha_info['pha'].rate_errors

        assert sum(pha_info['pha'].sys_errors == np.zeros_like(pha_info['pha'].rates)) == pha_info['bak'].n_channels

        assert pha_info['pha'].response_file.split('/')[-1] == 'glg_cspec_n3_bn080916009_v07.rsp'
        assert pha_info['pha'].scale_factor == 1.0

        assert pha_info['bak'].background_file is None

        # Test that we cannot get a bak file
        #
        #
        # with pytest.raises(KeyError):
        #
        #     _ = pha_info['bak'].background_file

        # Test that we cannot get a anc file
        # with pytest.raises(KeyError):
        #
        #     _ = pha_info['bak'].ancillary_file

            # Test that we cannot get a RSP file

        assert pha_info['bak'].response_file is None

        assert pha_info['bak'].ancillary_file is None

        # with pytest.raises(AttributeError):
        #      _ = pha_info['bak'].response_file

        assert pha_info['bak'].instrument == 'GBM_NAI_03'
        assert pha_info['bak'].mission == 'GLAST'

        assert pha_info['bak'].is_poisson() == False

        assert pha_info['bak'].n_channels == ogip.n_data_points
        assert pha_info['bak'].n_channels == len(pha_info['pha'].rates)

        assert len(pha_info['bak'].rate_errors) == pha_info['bak'].n_channels

        assert sum(pha_info['bak'].sys_errors == np.zeros_like(pha_info['pha'].rates)) == pha_info['bak'].n_channels

        assert pha_info['bak'].scale_factor == 1.0

        assert isinstance(pha_info['rsp'], Response)


def test_pha_files_in_generic_ogip_constructor_spec_number_in_arguments():
    with within_directory(__this_dir__):
        ogip = OGIPLike('test_ogip', pha_file='test.pha', spectrum_number=1)
        ogip.set_active_measurements('all')

        pha_info = ogip.get_pha_files()

        for key in ['pha', 'bak']:

            assert isinstance(pha_info[key], PHA)

        assert pha_info['pha'].background_file == 'test_bak.pha{1}'
        assert pha_info['pha'].ancillary_file == 'NONE'
        assert pha_info['pha'].instrument == 'GBM_NAI_03'
        assert pha_info['pha'].mission == 'GLAST'
        assert pha_info['pha'].is_poisson() == True
        assert pha_info['pha'].n_channels == ogip.n_data_points
        assert pha_info['pha'].n_channels == len(pha_info['pha'].rates)

        # Test that Poisson rates cannot call rate error
        with pytest.raises(AssertionError):

            _ = pha_info['pha'].rate_errors

        assert sum(pha_info['pha'].sys_errors == np.zeros_like(pha_info['pha'].rates)) == pha_info['bak'].n_channels
        assert pha_info['pha'].response_file.split('/')[-1] == 'glg_cspec_n3_bn080916009_v07.rsp'
        assert pha_info['pha'].scale_factor == 1.0

        assert pha_info['bak'].background_file is None

        # Test that we cannot get a bak file
        #
        # with pytest.raises(KeyError):
        #
        #     _ = pha_info['bak'].background_file
        #
        # Test that we cannot get a anc file
        # with pytest.raises(KeyError):
        #
        #     _ = pha_info['bak'].ancillary_file

        assert pha_info['bak'].response_file is None

        assert pha_info['bak'].ancillary_file is None

        # # Test that we cannot get a RSP file
        # with pytest.raises(AttributeError):
        #      _ = pha_info['bak'].response_file

        assert pha_info['bak'].instrument == 'GBM_NAI_03'
        assert pha_info['bak'].mission == 'GLAST'

        assert pha_info['bak'].is_poisson() == False

        assert pha_info['bak'].n_channels == ogip.n_data_points
        assert pha_info['bak'].n_channels == len(pha_info['pha'].rates)

        assert len(pha_info['bak'].rate_errors) == pha_info['bak'].n_channels

        assert sum(pha_info['bak'].sys_errors == np.zeros_like(pha_info['pha'].rates)) == pha_info['bak'].n_channels

        assert pha_info['bak'].scale_factor == 1.0

        assert isinstance(pha_info['rsp'], Response)


def test_ogip_energy_selection():
    with within_directory(__this_dir__):
        ogip = OGIPLike('test_ogip', pha_file='test.pha{1}')

        assert sum(ogip._mask) == sum(ogip._quality_to_mask())


        # Test that  selecting a subset reduces the number of data points
        ogip.set_active_measurements("10-30")

        assert sum(ogip._mask) == ogip.n_data_points
        assert sum(ogip._mask) < 128

        # Test selecting all channels
        ogip.set_active_measurements("all")

        assert sum(ogip._mask) == ogip.n_data_points
        assert sum(ogip._mask) == 128

        # Test channel setting
        ogip.set_active_measurements(exclude=['c0-c1'])

        assert sum(ogip._mask) == ogip.n_data_points
        assert sum(ogip._mask) == 126

        # Test mixed ene/chan setting
        ogip.set_active_measurements(exclude=['0-c1'])

        assert sum(ogip._mask) == ogip.n_data_points
        assert sum(ogip._mask) == 126

        # Test that energies cannot be input backwards
        with pytest.raises(AssertionError):
            ogip.set_active_measurements("50-30")

        with pytest.raises(AssertionError):
            ogip.set_active_measurements("c20-c10")

        with pytest.raises(AssertionError):
            ogip.set_active_measurements("c100-0")

        with pytest.raises(AssertionError):
            ogip.set_active_measurements("c1-c200")

        with pytest.raises(AssertionError):
            ogip.set_active_measurements("10-c200")


        ogip.set_active_measurements('reset')

        assert sum(ogip._mask) == sum(ogip._quality_to_mask())


def test_ogip_rebinner():
    with within_directory(__this_dir__):
        ogip = OGIPLike('test_ogip', pha_file='test.pha{1}')

        n_data_points = 128
        ogip.set_active_measurements("all")

        assert ogip.n_data_points == n_data_points

        ogip.rebin_on_background(min_number_of_counts=100)

        assert ogip.n_data_points < 128

        with pytest.raises(AssertionError):
            ogip.set_active_measurements('all')

        ogip.remove_rebinning()

        assert ogip._rebinner is None

        assert ogip.n_data_points == n_data_points


def test_simulating_data_sets():
    with within_directory(__this_dir__):

        ogip = OGIPLike('test_ogip', pha_file='test.pha{1}')

        n_data_points = 128
        ogip.set_active_measurements("all")

        ab = AnalysisBuilder(ogip)
        ab.build_point_source_jl()

        assert ogip._n_synthetic_datasets == 0

        new_ogip = ogip.get_simulated_dataset('sim')

        assert new_ogip.name == 'sim'
        assert ogip._n_synthetic_datasets == 1
        assert new_ogip.n_data_points == n_data_points

        assert new_ogip.n_data_points == sum(new_ogip._mask)
        assert sum(new_ogip._mask) == new_ogip.n_data_points
        assert new_ogip.tstart is None
        assert new_ogip.tstop is None
        assert 'cons_sim' in new_ogip.nuisance_parameters
        assert new_ogip.nuisance_parameters['cons_sim'].fix == True
        assert new_ogip.nuisance_parameters['cons_sim'].free == False

        pha_info = new_ogip.get_pha_files()

        assert 'pha' in pha_info
        assert 'bak' in pha_info
        assert 'rsp' in pha_info

        del ogip
        del new_ogip

        ogip = OGIPLike('test_ogip', pha_file='test.pha{1}')

        ab = AnalysisBuilder(ogip)
        ab.build_point_source_jl()

        # Now check that generationing a lot of data sets works

        sim_data_sets = [ogip.get_simulated_dataset('sim%d' % i) for i in range(100)]

        assert len(sim_data_sets) == ogip._n_synthetic_datasets

        for i, ds in enumerate(sim_data_sets):

            assert ds.name == "sim%d" % i
            assert sum(ds._mask) == sum(ogip._mask)
            assert ds._rebinner is None


def test_likelihood_ratio_test():
    with within_directory(__this_dir__):

        ogip = OGIPLike('test_ogip', pha_file='test.pha{1}')

        ogip.set_active_measurements("all")

        ab = AnalysisBuilder(ogip)
        ab.build_point_source_jl()

        jls = ab.build_point_source_jl()

        for key in ['normal', 'cpl']:

            jl = jls[key]

            res, _ = jl.fit(compute_covariance=False)

    lrt = LikelihoodRatioTest(jls['normal'], jls['cpl'])

    null_hyp_prob, TS, data_frame, like_data_frame = lrt.by_mc(n_iterations=50, continue_on_failure=True)