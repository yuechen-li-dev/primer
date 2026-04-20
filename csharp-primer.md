# C# Primer

A practical primer for writing modern, explicit, machine-friendly C# that stays readable, deterministic, and semantically honest.

This is not a generic C# tutorial. It is a house style and authoring subset for writing good code in our repos.

The goal is simple:

* Prefer clarity over cleverness.
* Prefer direct code over framework ceremony.
* Prefer modern language features when they make intent clearer.
* Prefer deterministic, inspectable systems over magic.
* Prefer real structure over faux architecture.

C# is good because it is boring by default. Keep that strength. Do not smuggle in old .NET habits, enterprise pattern cargo cults, or dynamic magic. Use modern features where they make the code more expressive of actual intent.

---

# 1. Core Philosophy

Write C# that is:

* explicit
* modern
* deterministic
* testable
* semantically direct
* boring in the good way

Do not write code that is merely "valid C#". Write code that reveals intent clearly.

Good code should make these things obvious:

* what the data is
* what the state transitions are
* what can fail
* what happens next
* what is policy versus mechanism

The best code is usually plain code with good naming and good shape.

---

# 2. Modern C# Is Preferred

Prefer modern C# features when they improve clarity and make the code more semantically expressive.

This includes features like:

* switch expressions
* pattern matching
* collection expressions
* target-typed new where it improves readability
* required members when appropriate
* expression forms when they are genuinely clearer
* records for immutable data shapes

Do not default to old .NET Framework-era code shape out of habit.

## Prefer this

```csharp
return kind switch
{
    TokenKind.Identifier => ParseIdentifier(),
    TokenKind.Number => ParseNumber(),
    TokenKind.String => ParseString(),
    _ => throw new InvalidOperationException($"Unexpected token kind: {kind}"),
};
```

Over this

```csharp
switch (kind)
{
    case TokenKind.Identifier:
        return ParseIdentifier();
    case TokenKind.Number:
        return ParseNumber();
    case TokenKind.String:
        return ParseString();
    default:
        throw new InvalidOperationException("Unexpected token kind: " + kind);
}
```

Both are valid. The first more directly expresses "this is a value selection by case." Use the form that best matches the intent.

## Prefer this

```csharp
var supportedKinds = [TokenKind.Identifier, TokenKind.Number, TokenKind.String];
```

Over this

```csharp
var supportedKinds = new List<TokenKind>
{
    TokenKind.Identifier,
    TokenKind.Number,
    TokenKind.String,
};
```

Use the newer form when it is clearer and not ambiguous.

Modern features are not "cool new shit" for their own sake. Use them because they produce better code shape.

---

# 3. Clarity First, Cleverness Last

Use the most direct construct that truthfully expresses the code.

Do not be clever with:

* overly compressed expressions
* nested LINQ pipelines
* reflection-driven dispatch
* generic abstraction layers that erase meaning
* magic framework attributes or hidden conventions

The code should be easy for a human to step through and easy for a model to extend safely.

If a construct saves lines but hides intent, it is not a win.

---

# 4. Plain Types Win

Prefer plain, concrete types.

## Classes

Use classes for normal behaviorful objects, services, stateful components, and domain entities where identity or controlled mutability matters.

## Records

Use records for immutable data shapes, value-like transport objects, diagnostic payloads, configuration snapshots, and other data-first types.

Records are especially good when value semantics and non-destructive updates match the domain.

## Structs

Treat structs as specialized tools, not defaults.

Use structs only when:

* the type is genuinely small and value-like
* copy behavior is acceptable and understood
* the semantics clearly benefit from value-type representation

Avoid mutable structs.

Avoid record struct unless there is a strong, concrete reason.

If unsure, use a class or record.

---

# 5. Inheritance Is Suspicious

Prefer composition over inheritance.

Inheritance is allowed when the domain genuinely demands a stable subtype relationship, but it is not the default modeling tool.

Do not create inheritance trees just because C# supports them.

Signs of bad inheritance:

* abstract base classes used only to share utility code
* deep hierarchies
* template-method ceremony for simple flows
* subclass proliferation to represent policy variants

Prefer:

* composition
* small interfaces when a real seam exists
* data + explicit dispatch
* switch expressions over tagged/domain variants when appropriate

---

# 6. Interfaces Are for Real Seams

Do not introduce interfaces preemptively.

An interface should exist because:

* there is a real alternate implementation
* there is a real test seam
* there is a real boundary between policy and mechanism

Do not write `IFoo` for every `Foo` out of habit.

Bad:

* one implementation forever
* interface exists only because "that is how enterprise C# is done"
* constructor injection of five single-use interfaces with trivial pass-through logic

Good:

* stable boundary
* real substitution value
* clear architectural seam

Concrete code is usually easier to understand and maintain.

---

# 7. Stay Away from Framework Garbage

Avoid old .NET cargo cult and framework-heavy patterns unless there is a compelling, concrete reason.

Strongly avoid:

* service locator patterns
* architecture astronaut layering
* repository pattern over things that are not actually repositories
* MediatR everywhere for ordinary control flow
* CQRS theater without real complexity justifying it
* reflection-driven registration and dispatch
* attribute magic that hides behavior
* runtime type scanning as a default mechanism
* dynamic invocation tricks
* "base service" and "manager" sludge

The more behavior is hidden in framework machinery, the worse the code is to reason about, test, and safely modify.

Prefer explicit construction, explicit flow, explicit calls, explicit registration.

---

# 8. Reflection, Dynamic Magic, and Hidden Behavior

Avoid reflection unless there is no simpler alternative and the value is overwhelming.

Reflection is usually a smell because it:

* hides real dependencies
* makes behavior harder to trace
* weakens compile-time guarantees
* complicates testing and tooling
* encourages framework-shaped code

The same applies to other dynamic or hidden-behavior mechanisms.

Avoid by default:

* reflection-based discovery
* magic registration by assembly scanning
* hidden attribute-driven wiring
* stringly typed member access
* dynamic dispatch where normal code would do

If behavior matters, it should usually be visible in normal code.

---

# 9. Nullability Is Mandatory

Nullable reference types should be enabled and treated seriously.

Do not casually suppress warnings.

The nullability annotations are part of the contract. Respect them.

Rules:

* model null honestly
* avoid `!` except when you can locally prove correctness
* prefer explicit validation at boundaries
* keep nullable flows tight and obvious
* do not shrug off warnings with blanket suppression

Bad:

```csharp
return node!.Parent!.Name!;
```

Better:

```csharp
if (node.Parent is null)
{
    return null;
}

return node.Parent.Name;
```

Or better still, model the contract so the ambiguity does not exist in the first place.

---

# 10. Exceptions Are Not Control Flow

Use exceptions for truly exceptional failures, violated invariants, impossible states, or hard boundary failures.

Do not use exceptions for normal branching or expected outcomes.

Expected failures should be represented explicitly through:

* result objects
* diagnostics
* booleans plus output values
* parse/try patterns
* domain-specific error payloads

Bad:

```csharp
try
{
    return Parse(text);
}
catch
{
    return null;
}
```

Better:

```csharp
if (!TryParse(text, out var value))
{
    return null;
}

return value;
```

Exceptions should mean something went wrong beyond ordinary domain flow.

---

# 11. Async Is for Real Asynchrony

Do not spread async mechanically.

Use async when there is real asynchronous work:

* I/O
* waiting on external systems
* true concurrency requirements

Do not make code async just because modern C# can.

Prefer synchronous code when the operation is fundamentally synchronous.

Avoid:

* viral async spread with no I/O reason
* fake async wrappers
* unnecessary `Task.Run`
* complicated async call chains for simple local work

Use `CancellationToken` when cancellation is meaningful at the boundary.
Do not thread tokens through every method pointlessly.

Use `ValueTask` only when justified by measurement or a well-understood hot path.
Default to `Task`.

---

# 12. LINQ in Moderation

LINQ is useful, but it turns into sludge quickly.

Use LINQ when it genuinely improves clarity for simple data transformations.

Avoid LINQ when:

* the pipeline becomes long
* the logic becomes stateful
* the query hides important control flow
* debugging becomes harder than a plain loop
* allocations and deferred execution semantics start mattering

A plain loop is often clearer.

Good:

```csharp
var names = people.Select(x => x.Name).ToArray();
```

Bad:

```csharp
var result = people
    .Where(x => x.IsActive)
    .GroupBy(x => x.TeamId)
    .OrderByDescending(g => g.Count())
    .SelectMany(g => g.Select(x => Transform(x, settings)))
    .Where(x => x.ShouldEmit)
    .ToDictionary(x => x.Key, x => x.Value);
```

That might be correct, but if it is hard to read, hard to step through, or hard to explain, rewrite it.

Prefer explicit intermediate values when they reveal intent.

---

# 13. Use Switch Expressions and Pattern Matching Aggressively but Sanely

Pattern matching and switch expressions are among the best modern C# features for clarity.

Use them when they encode intent better than old statement-heavy forms.

Examples:

* selecting a value by case
* discriminating domain shapes
* making impossible states obvious
* flattening branching into clearer expression form

These features help code read like meaning instead of mechanism.

Avoid only when the expression form becomes contorted or hides important work.

---

# 14. Collection Expressions and Literals

Use collection expressions when they make data construction shorter and clearer.

Prefer concise literal construction for obvious fixed data.

Examples:

```csharp
int[] values = [1, 2, 3, 4];
List<string> names = ["Ada", "Grace", "Linus"];
```

Do not avoid these out of outdated style inertia.

At the same time, do not abuse compact syntax when a more expanded form reveals intent better.

---

# 15. Naming Should Reveal Shape

Use names that make the role of the thing obvious.

A good name should communicate whether something is:

* data
* policy
* state
* parser
* builder
* diagnostic
* registry
* orchestrator
* runtime component

Avoid sludge names like:

* Manager
* Helper
* Utility
* Common
* BaseThing
* Stuff
* Processor when the actual role is more specific

Name things for their actual responsibility.

---

# 16. Prefer Explicit Construction

Prefer normal constructors and explicit setup over container magic.

Wiring should usually be visible in code.

Good:

```csharp
var parser = new FirmamentParser(diagnostics, registry);
var importer = new ImportOrchestrator(parser, lowerer, logger);
```

Bad:

* type scanning
* runtime auto-registration
* hidden constructor resolution chains
* gigantic service bootstrapping for a small tool or kernel

Simple construction is easier to debug and easier for author models to preserve.

---

# 17. Error Messages and Diagnostics Matter

Diagnostics should be:

* specific
* actionable
* stable
* normalized when appropriate
* easy to assert in tests

Do not emit vague messages like:

* Invalid input
* Something went wrong
* Bad state

Prefer messages that identify:

* what failed
* where it failed
* why it failed
* what the relevant value was

If the repo uses diagnostic codes or normalized wording, follow that rigorously.

---

# 18. Testing Must Be Deterministic

Prefer xUnit-style deterministic tests with clear fixtures and inspectable outputs.

Encode this explicitly:

* deterministic seeds
* stable test inputs
* artifact outputs when useful
* assertions on meaningful behavior, not vibes
* test logs and manifests when diagnosing complicated flows

Prefer real harnesses over brittle mock theater.

Mock only where the seam is real and the mock clarifies behavior.

Do not build giant fake worlds just to avoid constructing a few real objects.

If a system is stateful, make the state transitions inspectable.

---

# 19. Performance Is Evidence-Based

Do not optimize preemptively.

Avoid performance goblin behavior like:

* introducing `Span<T>` everywhere without need
* object pooling by reflex
* `ref` and `in` everywhere for style points
* allocation paranoia before profiling
* making code cryptic to chase imagined micro-gains

Write clear code first.
Measure.
Then optimize where the evidence says it matters.

Low-level tools are good when justified. They are not badges of seriousness.

---

# 20. Serialization and Data Contracts Should Be Boring

Serialized shapes should be explicit and stable.

Avoid clever serialization tricks, polymorphic magic, and reflection-heavy customization unless absolutely necessary.

Prefer:

* explicit DTOs
* explicit field/property intent
* explicit versioning strategy where relevant
* stable contracts

The easier a payload is to inspect and reason about, the better.

---

# 21. Generics Should Clarify, Not Obscure

Use generics when they express a real reusable abstraction.

Do not use generics to sound advanced.

Avoid:

* deeply generic infrastructure nobody can mentally execute
* abstracting over tiny differences too early
* generic helper layers that erase domain meaning

A duplicated but clear implementation is often better than a hyper-abstract generic one.

---

# 22. Prefer Local Reasoning

Code should be understandable from nearby context.

Avoid designs where understanding one method requires chasing:

* three partial classes
* two base types
* attribute metadata
* DI registration
* reflection registration
* convention-based runtime discovery

Keep logic close to where it matters.

Local reasoning makes code safer for humans and machines.

---

# 23. Follow the Existing Shape of the Repo

Repo-specific conventions outrank generic best practices.

If a repo has an established pattern that is clean and intentional, match it.
Do not import unrelated style from random blog-post C#.

The goal is coherence.

A codebase written in one strong style is much easier to extend safely than a codebase that reflects every tutorial the model has ever seen.

---

# 24. Red Flags

If you see code drifting toward these patterns, stop and reconsider:

* interface for every class
* dependency injection for everything
* reflection or assembly scanning by default
* old-style verbose branching where modern expressions are clearer
* giant LINQ chains
* inheritance-heavy object models
* async without real async work
* exception-driven normal flow
* helper/manager/service sludge naming
* framework ceremony larger than the actual domain logic
* "reusable" abstractions with no second use
* code that looks more like architecture than software

---

# 25. Green Flags

Good C# in our repos often looks like this:

* plain types with clear names
* records for immutable data
* classes for concrete behavior
* switch expressions and pattern matching for domain logic
* collection expressions for obvious literals
* explicit construction
* explicit diagnostics
* deterministic tests
* simple control flow
* direct data flow
* minimal magic
* modern syntax used in service of clarity

---

# 26. Preferred Defaults

When in doubt:

* prefer modern syntax if it improves clarity
* prefer explicit over implicit magic
* prefer concrete types over interfaces
* prefer composition over inheritance
* prefer sync over async unless async is real
* prefer loops over LINQ sludge
* prefer result-style handling for expected failure
* prefer nullable honesty over suppression
* prefer plain construction over containers
* prefer deterministic tests over mocks
* prefer measurable optimization over imagined optimization

---

# 27. The Standard

The standard is not "write clever C#."

The standard is:

Write C# that a careful engineer can read, trust, debug, extend, and hand to another model without it mutating into framework soup.

Use modern language features because they let the code speak more clearly.
Avoid dynamic tricks because they make the code lie about where behavior lives.

Good C# should feel solid, unsurprising, and honest.

That is the target.
