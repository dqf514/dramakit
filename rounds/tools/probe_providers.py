"""Where would a stop event reach the model client?

A stage that makes one long call has no seam to check between items, so
asking it to stop only takes effect when the call returns - a minute or
more, and the stage is written up as finished rather than refused. The
client that makes the call is the place that can let go sooner, so this
reads how it is built and how a provider hands one out.
"""
import inspect
import sys

sys.path.insert(0, r"E:\dramakit")

from dramakit.providers import Providers

print("=== Providers.__init__ ===")
print(inspect.getsource(Providers.__init__)[:900])
print()
print("=== llm_for ===")
print(inspect.getsource(Providers.llm_for)[:700])
print()
print("=== 属性 ===")
print([a for a in dir(Providers) if not a.startswith("__")][:24])
