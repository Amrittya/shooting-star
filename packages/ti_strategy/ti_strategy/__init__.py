"""Strategy framework and concrete strategies for Shooting Star.

One Strategy base class serves both option-selling and option-buying strategies;
differences (defined vs undefined risk, exit mechanics, sizing) are composed via
Signal / ExitRule / Sizer primitives, not by branching the base class.
"""

__version__ = "0.1.0"
