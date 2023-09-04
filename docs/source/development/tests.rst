.. _writing-tests:

Writing Tests
=============

Every feature you add must have tests. Use Django's :code:`TestCase` and its
subclasses to write your tests. Your tests should reside in root :code:`tests`
directory, i.e., do not put your tests in apps or modules.

Here are few tips while writing tests:

*   Run your tests multiple times to ensure they are not flaky.
*   Run your tests in parallel and make sure nothing breaks.
*   Make sure your tests are **fast**. Monitor your tests carefully and
    eliminate slow tests.
*   Check coverage and make sure everything is covered. Keep in mind that
    having a high coverage does not necessarily mean everything is tested.
*   If exposed as an API, your feature should have end-to-end tests as well as
    unit tests.
