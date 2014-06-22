"""
.. module:: soap.analysis.core
    :synopsis: Analysis classes.
"""
import math

import gmpy2

from soap import logger, flopoco
from soap.context import context
from soap.common import DynamicMethods, Flyweight
from soap.semantics.functions import error_eval, luts


class Analysis(DynamicMethods, Flyweight):
    """A base class that analyses expressions for the quality metrics.

    This base class is not meant to be instantiated, but to be subclassed
    with methods to provide proper analysis.
    """

    def __init__(self, expr_set, var_env, precs=None):
        """Analysis class initialisation.

        :param expr_set: A set of expressions or a single expression.
        :type expr_set: `set` or :class:`soap.expression.Expr`
        :param var_env: The ranges of input variables.
        :type var_env: dictionary containing mappings from variables to
            :class:`soap.semantics.error.Interval`
        :param precs: Precisions used to evaluate the expressions, defaults to
            the return value of :member:`precisions`.
        :type precs: list of integers
        """
        super().__init__()
        self.expr_set = expr_set
        self.var_env = var_env
        self.precs = precs if precs else self.precisions()

    def precisions(self):
        """Returns the precisions being used.

        :returns: a list of integers indicating precisions.
        """
        return [context.precision]

    def analyse(self):
        """Analyses the set of expressions with input ranges and precisions
        provided in initialisation.

        :returns: a list of dictionaries each containing results and the
            expression.
        """
        try:
            return self.result
        except AttributeError:
            pass
        analysis_names, analysis_methods, select_methods = self.methods()
        logger.debug('Analysing results.')
        result = []
        i = 0
        n = len(self.expr_set) * len(self.precs)
        for p in self.precs:
            for t in self.expr_set:
                i += 1
                logger.persistent('Analysing', '%d/%d' % (i, n),
                                  l=logger.levels.debug)
                analysis_dict = {'expression': t}
                for name, func in zip(analysis_names, analysis_methods):
                    analysis_dict[name] = func(t, p)
                result.append(analysis_dict)
        logger.unpersistent('Analysing')
        result = sorted(
            result, key=lambda k: tuple(k[n] for n in analysis_names))
        for analysis_dict in result:
            for n, f in zip(analysis_names, select_methods):
                analysis_dict[n] = f(analysis_dict[n])
        self.result = result
        return self.result

    @classmethod
    def names(cls):
        method_list = cls.list_method_names(lambda m: m.endswith('_analysis'))
        names = []
        for m in method_list:
            m = m.replace('_analysis', '')
            names.append(m)
        return names

    def methods(self):
        method_names = self.names()
        analysis_methods = []
        select_methods = []
        for m in method_names:
            analysis_methods.append(getattr(self, m + '_analysis'))
            select_methods.append(getattr(self, m + '_select'))
        return method_names, analysis_methods, select_methods


class ErrorAnalysis(Analysis):
    """This class provides the analysis of error bounds.

    It is a subclass of :class:`Analysis`.
    """
    def error_analysis(self, t, p):
        return error_eval(t, self.var_env, p)

    def error_select(self, v):
        with gmpy2.local_context(gmpy2.ieee(64), round=gmpy2.RoundAwayZero):
            return float(max(abs(v.e.min), abs(v.e.max)))


class AreaAnalysis(Analysis):
    """This class provides the analysis of area estimation.

    It is a subclass of :class:`Analysis`.
    """
    def area_analysis(self, t, p):
        bound = error_eval(t, self.var_env, p).v
        bound_max = max(abs(bound.min), abs(bound.max), 1)
        exp_max = math.floor(math.log(bound_max, 2))
        try:
            we = int(math.ceil(math.log(exp_max + 1, 2) + 1))
        except ValueError:
            we = 1
        we = max(we, flopoco.we_min)
        return luts(t, we, p)

    def area_select(self, v):
        return v


def pareto_frontier_2d(s, keys=None):
    """Generates the 2D Pareto Frontier from a set of results.

    :param s: A set/list of comparable things.
    :type s: container
    :param keys: Keys used to compare items.
    :type keys: tuple or list
    """
    if keys:
        a = keys[1]
        sort_key = lambda e: tuple(e[k] for k in keys)
    else:
        a = 1
        sort_key = None
    s = sorted(s, key=sort_key)
    frontier = s[:1]
    for i, m in enumerate(s[1:]):
        if m[a] < frontier[-1][a]:
            frontier.append(m)
    return frontier


class AreaErrorAnalysis(ErrorAnalysis, AreaAnalysis):
    """Collect area and error analysis.

    It is a subclass of :class:`ErrorAnalysis` and :class:`AreaAnalysis`.
    """
    def frontier(self):
        """Computes the Pareto frontier from analysed results.
        """
        return pareto_frontier_2d(self.analyse(), keys=self.names())


class VaryWidthAnalysis(AreaErrorAnalysis):
    """Collect area and error analysis.

    It is a subclass of :class:`ErrorAnalysis` and :class:`AreaAnalysis`.
    """
    def precisions(self):
        """Allow precisions to vary in the range of `flopoco.wf_range`."""
        return flopoco.wf_range
