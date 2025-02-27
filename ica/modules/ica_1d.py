#
# Created by Jibran Haider.
#
"""This module contains functions for performing FastICA on 1D data along with pre-processing and post-processing steps.

Below is a list of the functions in this module.

Routine Listings
----------------
ica_setup(source_noise, source_nonG)
    Set up signal mixture for ICA.
ica_prewhiten(mix_signal, kbin_size=None)
    Custom prewhitening of the signal mixture in k-space.
fastica_run(mix, num_comps, max_iter=1e4, tol=1e-5, 
        fun='logcosh', whiten='unit-variance', algo='parallel')
    Run FastICA on the signal mixture.

ica_match(source_comps, ica_comps)
    Match the source components to the ICA components.
ica_scaleandsign(source_comps, ica_comps)
    Scale and sign the ICA components to match the source components.
ica_scaleoffset(source_comps, ica_comps)
    Scale and offset the ICA components to match the source components.
ica_swap(source_comps, ica_comps)
    Swap the ICA components to match the source components.

ica_all(field_g, field_ng, 
            max_iter=1e4, tol=1e-5, fun='logcosh', whiten='unit-variance', algo='parallel', 
                prewhiten = False, wbin_size = None)
    Preprocess signals, run ICA, and perform postprocessing on the given fields.
ica_all_unknownmix(obs_signal, num_comps=None, 
            max_iter=1e5, tol=1e-5, fun='logcosh', whiten='unit-variance', algo='parallel', 
                prewhiten = False, wbin_size = None)
    Preprocess signals, run ICA, and perform postprocessing on an apriori unknown mixture of signals.

Notes
-----
"""

import numpy as np
import scipy.stats as stats
from sklearn.decomposition import FastICA

from ica.modules.validate_1d import calculate_residuals_ica as resid


############################################################
#
# PRE-ICA PROCESSING
#
############################################################
def ica_setup(source_noise, source_nonG):
    """Set up signal mixture for ICA.

    Parameters
    ----------
    source_noise : array
        GRF component of the signal mixture.
    source_nonG : array
        PNG component of the signal mixture.

    Returns
    -------
    mix_signal : array
        Mixed signal.
    source_comps : array
        Source components.
    num_comps : int
        Number of source components.

    Notes
    -----
        source_noise    :   grf generated using gaussianfield [in Notebook Setup above]
        source_nonG     :   returns n columns corresponding to n gaussian peaks that are shifted by xPeak/xc relative to 0 (and scaled by the size of the field)
        source_comps    :   array of source component arrays
        num_comps       :   num of different source signals/components, i.e. GRF & no. of peaks
        num_samples     :   num of observations (has to be >= num_comps)
        mix_matrix      :   mixing matrix generated randomly with entries over [0.5, 1)
        mix_signal      :   resulting mixed/observed signals (not prewhitened)
    """

    source_comps = np.vstack([source_nonG, source_noise])
    num_comps = source_comps.shape[0]
    num_samples = num_comps

    mix_matrix = (1.0+np.random.random((num_samples, num_comps)))/2.0
    mix_signal = np.dot(mix_matrix, source_comps) # mixed signals

    return mix_signal, source_comps, num_comps

def ica_prewhiten(mix_signal, kbin_size=None):
    """Custom prewhitening of the signal mixture in k-space.

    Handling the two observed signals separately. 
    Preprocessing involves mean subtraction and dividing by the variance (in k-space).
    """

    s1_pre = mix_signal[0, :]
    s2_pre = mix_signal[1, :]
    size = s1_pre.size

    s1ft = np.fft.rfft(s1_pre)
    s2ft = np.fft.rfft(s2_pre)
    kfreq = np.fft.rfftfreq(size) * size
    k_size = kfreq.size
    # k_size = size//2 + 1
    
    s1ft_amps = np.abs(s1ft)
    s2ft_amps = np.abs(s2ft)
    s1ft_power = s1ft_amps**2
    s2ft_power = s2ft_amps**2
    
    if kbin_size==None:
        nkbins = int(k_size/50)
    else:
        nkbins = int(k_size//kbin_size)
    kbins = np.linspace(0, k_size, nkbins+1)
    kbins_size = kbins.size
    kvals = 0.5 * (kbins[1:] + kbins[:-1])
    
    s1ft_Apower_bins, _, _ = stats.binned_statistic(kfreq, s1ft_power,
                                        statistic = "mean",
                                        bins = kbins)
    s2ft_Apower_bins, _, _ = stats.binned_statistic(kfreq, s2ft_power,
                                        statistic = "mean",
                                        bins = kbins)

    # s1ft_Atotpower_bins = s1ft_Apower_bins * (kbins[1:] - kbins[:-1])
    # s1ft_Atotpower_bins = s2ft_Apower_bins * (kbins[1:] - kbins[:-1])

    for i in range (kbins_size-1):
        kl = int(kbins[i])
        kh = int(kbins[i+1])
        s1ft[kl:kh] = s1ft[kl:kh] / np.sqrt(s1ft_Apower_bins[i])
        s2ft[kl:kh] = s2ft[kl:kh] / np.sqrt(s2ft_Apower_bins[i])
    
    s1_white = np.fft.irfft(s1ft)
    s2_white = np.fft.irfft(s2ft)
    
    # print(np.mean(sample1_pre), np.mean(sample2_pre))

    # for i in range(kc_size-1):
    #     count = i+1
    #     klow = int(kc[i])
    #     khigh = int(kc[i+1])
        
    #     sample1_sqrtpower = np.absolute(sample1_ft[klow:khigh]) #k-space variance
    #     sample1_ft[klow:khigh] = sample1_ft[klow:khigh] * ( size )**(1/2) / sample1_sqrtpower  # Whitening the field
        
    #     sample2_sqrtpower = np.absolute(sample2_ft[klow:khigh])
    #     sample2_ft[klow:khigh] = sample2_ft[klow:khigh] * ( size )**(1/2) / sample2_sqrtpower

    # print(np.mean(sample1), np.mean(sample2))
    # m1 = np.mean(sample1)
    # sample1 = sample1 - m1 #Subtracting the mean
    # # Sample 2 - same procedure as above
    # m2 = np.mean(sample2)
    # sample2 = sample2 - m2
    # print(np.mean(sample1), np.mean(sample2))

    # Mix the samples back again
    mix_signal = np.vstack([s1_white, s2_white])

    return mix_signal




############################################################
# 
# FASTICA
# 
############################################################
def fastica_run(mix, num_comps, max_iter=1e4, tol=1e-5, 
        fun='logcosh', whiten='unit-variance', algo='parallel'):
    """Initialize FastICA with given params.

    Parameters
    ----------
    mix : np.ndarray, shape (n, m)
        nxm numpy array containing the mixed/observed signals.
    num_comps : int
        Number of components to extract.
    max_iter : int, optional
        Maximum number of iterations to run FastICA. The default is 1e4.
    tol : float, optional
        Tolerance for convergence. The default is 1e-5.
    fun : str, optional
        Cost-function to use for ICA. The default is 'logcosh'.
    whiten : str, optional
        Whitening method to use. The default is 'unit-variance'.
    algo : str, optional
        Algorithm to use for ICA. The default is 'parallel'.

    Returns
    -------
    sources.T : np.ndarray, shape (m, n)
        mxn numpy array containing the extracted source components.

    Notes
    -----
    Logcosh is negentropy.
    """
    
    # , white='unit-variance'
    transformer = FastICA(n_components=num_comps, algorithm=algo, whiten=whiten, max_iter=max_iter, tol=tol, fun=fun)

    # run FastICA on observed (mixed) signals
    sources = transformer.fit_transform(mix.T)

    print(transformer.components_.shape)
    
    return sources.T




# ############################################################
# #
# # POST-ICA PROCESSING
# #
# ############################################################
# def match_rescale_ica(src_comps, ica_comps):
#     """Match and rescale ICA components to the original source components.

#     Parameters
#     ----------
#     src_comps : dict
#         Dictionary containing the source components labeled "GRF" and "PNG".
#     ica_comps : np.ndarray, shape (2, n)
#         2xn numpy array containing the ICA extracted components.

#     Returns
#     -------
#     matched_comps : dict
#         Dictionary of properly labeled, rescaled, and sign-inverted ICA components.
#     """

#     def calc_residual(a, b):
#         """
#         Calculate the residual between vectors a and b.

#         This function rescales b to match the variance of a and then calculates
#         the residual, which is insensitive to sign differences.
#         """
#         b_rescaled = (b / np.std(b)) * np.std(a)
#         b_norm = b_rescaled / np.linalg.norm(b_rescaled)
#         projection = np.dot(a, b_norm)
#         return 1 - np.abs(projection / np.linalg.norm(a))

#     def rescale_invert(a, b):
#         """
#         Rescale and invert vector b to match vector a.

#         This function rescales b to match the variance of a and inverts its sign
#         if the projection of b onto a is negative.
#         """
#         scale_factor = np.dot(a, b) / np.dot(b, b)
#         return scale_factor * b

#     matched_comps = {}
#     for label, src_comp in src_comps.items():
#         min_residual = np.inf
#         best_match = None
#         best_match_idx = -1
        
#         for idx, ica_comp in enumerate(ica_comps.T):
#             residual = calc_residual(src_comp, ica_comp)
#             if residual < min_residual:
#                 min_residual = residual
#                 best_match = ica_comp
#                 best_match_idx = idx
                
#         rescaled_inverted_comp = rescale_invert(src_comp, best_match)
#         matched_comps[label] = rescaled_inverted_comp
#         ica_comps = np.delete(ica_comps, best_match_idx, axis=1)

#     return matched_comps

# def test_match_rescale_ica():
#     src_comps = {
#         "GRF": np.array([1, 2, 3, 4]),
#         "PNG": np.array([5, 6, 7, 8]),
#     }

#     ica_comps = np.array([
#         [1.5, 5.5],
#         [2.5, 6.5],
#         [3.5, 7.5],
#         [4.5, 8.5],
#     ])

#     matched_comps = match_rescale_ica(src_comps, ica_comps)

#     assert np.allclose(matched_comps["GRF"], src_comps["GRF"], atol=1e-6)
#     assert np.allclose(matched_comps["PNG"], src_comps["PNG"], atol=1e-6)


# def OLD_match_ica_comps(src_comps, ext_comps):
#     """Match and rescale ICA-extracted components to the original source components.
    
#     Parameters
#     ----------
#     src_comps : dict
#         Dictionary containing the source components labeled "GRF" and "PNG".
#     ext_comps : np.ndarray
#         2xn numpy array containing the ICA-extracted components.
    
#     Returns
#     -------
#     matched_comps : dict
#         Dictionary of properly labeled, rescaled, and sign-inverted ICA components.
#     """

#     def calc_resid(a, b):
#         """Calculate the scalar residual between two vectors."""
#         a_norm = a / np.linalg.norm(a)
#         projection = np.dot(b, a_norm)
#         return 1 - np.abs(projection / np.linalg.norm(a))

#     def rescale_inv(a, b):
#         """Rescale and invert one vector to match another."""
#         scale_factor = np.dot(a, b) / np.dot(b, b)
#         return scale_factor * b

#     matched_comps = {}
#     for label, src_comp in src_comps.items():
#         min_resid = np.inf
#         best_match = None
#         best_match_idx = -1
        
#         for idx, ext_comp in enumerate(ext_comps.T):
#             # Calculate residuals for the extracted component and its sign-inverted version
#             resid = calc_resid(src_comp, ext_comp)
#             resid_inv = calc_resid(src_comp, -ext_comp)
            
#             # Choose the smaller residual and update the extracted component if needed
#             if resid_inv < resid:
#                 resid = resid_inv
#                 ext_comp = -ext_comp

#             # Update the best match if the current residual is smaller
#             if resid < min_resid:
#                 min_resid = resid
#                 best_match = ext_comp
#                 best_match_idx = idx
                
#         # Rescale and invert the best matching component
#         rescaled_inv_comp = rescale_inv(src_comp, best_match)
#         matched_comps[label] = rescaled_inv_comp
#         ext_comps = np.delete(ext_comps, best_match_idx, axis=1)

#     return matched_comps

def ica_match(source_comps, ica_src):
    """Swap, scale, and sign-invert the ICA components to match the source components.

    Parameters
    ----------
    source_comps : np.ndarray, shape (2, n)
        2xn numpy array containing the source components.
    ica_src : np.ndarray, shape (2, n)
        2xn numpy array containing the ICA components.

    Returns
    -------
    ica_sources : np.ndarray, shape (2, n)
        2xn numpy array containing the ICA components with the scaled and inverted components.    
    """

    ica_sources = np.ndarray.copy(ica_src)

    ica_sources = ica_swap(source_comps, ica_sources)
    ica_sources, src_max, ica_max = ica_scaleandsign(source_comps, ica_sources)
    # ica_sources, src_max, ica_max = ica_scaleoffset(source_comps, ica_sources)

    return ica_sources, src_max, ica_max

def ica_scaleandsign(source_comps, ica_src):
    """Scale and invert the sign of the ICA components to match the source components.

    Parameters
    ----------
    source_comps : np.ndarray, shape (2, n)
        2xn numpy array containing the source components.
    ica_src : np.ndarray, shape (2, n)
        2xn numpy array containing the ICA components.

    Returns
    -------
    ica_sources : np.ndarray, shape (2, n)
        2xn numpy array containing the ICA components with the scaled and inverted components.    
    """
    
    # print('\nBeginning flip...')
    ica_sources = np.ndarray.copy(ica_src)
    ica_sources, src_max, ica_max = ica_scaleoffset(source_comps, ica_sources)
    icaneg_sources, src_max, ica_max = ica_scaleoffset(source_comps, -ica_sources)

    srcng = source_comps[0, :]
    srcg = source_comps[1, :]
    icang = ica_sources[0, :]
    icag = ica_sources[1, :]
    icanegng = icaneg_sources[0, :]
    icanegg = icaneg_sources[1, :]

    dist_ngng = np.linalg.norm(srcng - icang, 1)
    dist_neg_ngng = np.linalg.norm(srcng - icanegng, 1)
    dist_gg = np.linalg.norm(srcg - icag, 1)
    dist_neg_gg = np.linalg.norm(srcg - icanegg, 1)
    
    if dist_gg > dist_neg_gg:
        # print('dist_gg:', dist_gg, ' | dist_neg_gg:', dist_neg_gg)
        icag = icanegg
        # print('Gauss sign flipped!')

    if dist_ngng > dist_neg_ngng:
        # print('dist_ngng:', dist_ngng, ' | dist_neg_ngng:', dist_neg_ngng)
        icang = icanegng
        print('NonG sign flipped!')

    ica_sources[0, :], ica_sources[1, :] = icang, icag
    
    # print('...ending flip.\n')
    return ica_sources, src_max, ica_max

def ica_scaleoffset(source_comps, ica_src):
    """Scale and offset the ICA components to match the source components.

    Parameters
    ----------
    source_comps : np.ndarray, shape (2, n)
        2xn numpy array containing the source components.
    ica_src : np.ndarray, shape (2, n)
        2xn numpy array containing the ICA components.

    Returns
    -------
    ica_sources : np.ndarray, shape (2, n)
        2xn numpy array containing the ICA components with the scaled and offset components.    
    """

    ica_sources = np.ndarray.copy(ica_src)
    src_ng = source_comps[0]
    src_g = source_comps[1]
    ica_ng = ica_sources[0]
    ica_g = ica_sources[1]

    icang_std = np.std(ica_ng)
    icang_mean = np.mean(ica_ng)
    srcng_std = np.std(src_ng)
    srcng_mean = np.mean(src_ng)
    icag_std = np.std(ica_g)
    icag_mean = np.mean(ica_g)
    srcg_std = np.std(src_g)
    srcg_mean = np.mean(src_g)
    
    ica_ng = ((ica_ng - icang_mean) / icang_std) 
    ica_ng = (ica_ng * srcng_std) + srcng_mean
    ica_g = ((ica_g - icag_mean) / icag_std) 
    ica_g = (ica_g * srcg_std) + srcg_mean

    src_ng_max = np.abs(src_ng).max()
    src_g_max = np.abs(src_g).max()
    src_max = np.abs(source_comps).max()
    ica_ng_max = np.abs(ica_ng).max()
    ica_g_max = np.abs(ica_g).max()
    ica_max = np.abs([ica_ng, ica_g]).max()

    # ng = ica_sources[0, :]
    # ng = ng * ( src_ng_max / ica_ng_max )
    # g = ica_sources[1, :]
    # g = g * ( src_g_max / ica_g_max )

    # ica_ng_max = np.abs(ng).max()
    # ica_g_max = np.abs(g).max()
    # ica_max = np.abs([ng, g]).max()
    
    ica_sources[0, :] = ica_ng; ica_sources[1, :] = ica_g

    return ica_sources, [src_max, src_ng_max, src_g_max], [ica_max, ica_ng_max, ica_g_max]

def ica_swap(source_comps, ica_src):
    """Swap the ICA components to match the source components.

    Parameters
    ----------
    source_comps : np.ndarray, shape (2, n)
        2xn numpy array containing the source components.
    ica_src : np.ndarray, shape (2, n)
        2xn numpy array containing the ICA components.

    Returns
    -------
    ica_sources : np.ndarray, shape (2, n)
        2xn numpy array containing the ICA components with the swapped components.  
    """
    
    # print('\nBeginning swap...')
    ica_sources = np.ndarray.copy(ica_src)

    srcng = source_comps[0, :]
    srcg = source_comps[1, :]
    ica0 = ica_sources[0, :]
    ica1 = ica_sources[1, :]

    dist_ng0 = resid(srcng, ica0)
    dist_ng1 = resid(srcng, ica1)
    # dist_ng0 = np.linalg.norm(srcng**2 - ica0**2, 1)
    # dist_ng1 = np.linalg.norm(srcng**2 - ica1**2, 1)
    dist_g0 = np.linalg.norm(srcg**2 - ica0**2, 1)
    dist_g1 = np.linalg.norm(srcg**2 - ica1**2, 1)

    # print('dist nong->ica1:', dist_ng1, ' | dist nong->ica0:', dist_ng0)
    # print('dist g->ica0:', dist_g0, ' | dist g->ica1:', dist_g1)
    
    if dist_ng0 > dist_ng1:
        # print('dist nong->ica1:', dist_ng1, ' | dist nong->ica0:', dist_ng0)
        # print('dist g->ica0:', dist_g0, ' | dist g->ica1:', dist_g1)
        ica_sources = np.flip(ica_sources, 0)
        print('Swapped!')

    # icang, icag = ica_sources[0, :], ica_sources[1, :]
    # dist_ngng = np.linalg.norm(srcng**2 - icang**2, 1)
    # print('dist nong->icang:', dist_ngng)
    
    # print('...ending swap.\n')
    return ica_sources




############################################################
#
# ALTOGETHER
#
############################################################
def ica_all(field_g, field_ng, 
            max_iter=1e4, tol=1e-5, fun='logcosh', whiten='unit-variance', algo='parallel', 
                prewhiten = False, wbin_size = None):
    """Preprocess signals, run ICA, and perform postprocessing on the given fields.

    Parameters
    ----------
    field_g : np.ndarray, shape (n, m)
        n x m numpy array containing the field data for the Gaussian source.
    field_ng : np.ndarray, shape (n, m)
        n x m numpy array containing the field data for the non-Gaussian source.
    max_iter : int, optional
        Maximum number of iterations to run ICA. The default is 1e4.
    tol : float, optional
        Tolerance for ICA convergence. The default is 1e-5.
    fun : str, optional
        The functional form of the G function used in the ICA algorithm. The default is 'logcosh'.
    whiten : str, optional
        The whitening method to use. The default is 'unit-variance'.
    algo : str, optional
        The algorithm to use. The default is 'parallel'.
    prewhiten : bool, optional
        Whether to prewhiten the data before running ICA. The default is False.
    wbin_size : int, optional
        The size of the bins to use for prewhitening. The default is None.

    Returns
    -------
    src : np.ndarray, shape (2, n)
        2xn numpy array containing the source components.
    ica_src : np.ndarray, shape (2, n)
        2xn numpy array containing the ICA components.
    src_max : np.ndarray, shape (2,)
        2x1 numpy array containing the maximum values of the source components.
    ica_max : np.ndarray, shape (2,)
        2x1 numpy array containing the maximum values of the ICA components.
    mix_signal : np.ndarray, shape (2, n)
        2xn numpy array containing the mixed signals.
    ica_src_og : np.ndarray, shape (2, n)
        2xn numpy array containing the ICA components before postprocessing.    
    """
    
    mix_signal_pre, src, num_comps = ica_setup(field_g, field_ng)
    if prewhiten:
        mix_signal = ica_prewhiten(mix_signal_pre, wbin_size)
    else:
        mix_signal = mix_signal_pre

    ica_src_og = fastica_run(mix_signal, num_comps, max_iter=max_iter, tol=tol, fun=fun, whiten=whiten, algo=algo)
    
    ica_src, src_max, ica_max = ica_match(src, ica_src_og)

    return src, ica_src, np.array([src_max, ica_max]), np.array([mix_signal_pre, mix_signal]), ica_src_og


def ica_all_unknownmix(obs_signal, num_comps=None, 
            max_iter=1e5, tol=1e-5, fun='logcosh', whiten='unit-variance', algo='parallel', 
                prewhiten = False, wbin_size = None):
    """Preprocess signals, run ICA, and perform postprocessing on an apriori unknown mixture of signals.

    Parameters
    ----------
    obs_signal : np.ndarray, shape (n, m)
        n x m numpy array containing the observed signals.
    num_comps : int, optional
        The number of components to use. The default is None.
    max_iter : int, optional
        Maximum number of iterations to run ICA. The default is 1e5.
    tol : float, optional
        Tolerance for ICA convergence. The default is 1e-5.
    fun : str, optional
        The functional form of the G function used in the ICA algorithm. The default is 'logcosh'.
    whiten : str, optional
        The whitening method to use. The default is 'unit-variance'.
    algo : str, optional
        The algorithm to use. The default is 'parallel'.
    prewhiten : bool, optional
        Whether to prewhiten the data before running ICA. The default is False.
    wbin_size : int, optional
        The size of the bins to use for prewhitening. The default is None.

    Returns
    -------
    ica_src : np.ndarray, shape (2, n)
        2xn numpy array containing the ICA components.
    """

    if prewhiten:
        obs_signal = ica_prewhiten(obs_signal, wbin_size)

    ica_src_og = fastica_run(obs_signal, num_comps, max_iter=max_iter, tol=tol, fun=fun, whiten=whiten, algo=algo)

    ica_src = ica_src_og
    # ica_src, src_max, ica_max = ica_restore(src, ica_src_og)

    return ica_src
