Adding new views
================

Using provided ViewSet
----------------------

**Always** subclass the :code:`asu.utils.views.ExtendedViewSet` to create new views.
This specific implementation has few advantages:

*   You can dispatch multiple view actions at once using the relevant class
    attribute that contains a mapping between actions and attributes. These
    attributes are:

    * :code:`serializer_classes`

    Mapping between serializer classes and actions.

    * :code:`filterset_classes`

    Mapping between actions and filtersets, only makes sense if your action
    lists something.

    * :code:`schemas`

    Mapping between actions and their OpenAPI overrides. Make sure the
    OpenAPI definitions have their own module in related app.

    * :code:`scopes`

    OAuth 2.0 scopes required for this action to be performed. Make sure you
    have specified :code:`asu.auth.permissions.RequireScope` in
    :code:`permission_classes`. If you require any scope, you are likely to
    require user for the action. For that, also include
    :code:`asu.auth.permissions.RequireUser`.

*   You can inherit ViewSet mixins by using :code:`mixins` class attribute. You
    don't have to import any mixins from :code:`rest_framework`.

*   You can use :code:`get_action_save_response` method to easily handle
    serializer create & update requests in actions. This method handles all the
    validation and serialization and reduces repetition so that you don't have
    to write this over and over:

    .. code-block:: python

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


Other recommendations
---------------------

*   Make sure bulk of the business logic is contained within models and
    serializers. The ViewSet itself should only be used to dispatch serializers and
    model manager methods.

*   Follow standard URL structure for RESTful applications. You may use nested
    ViewSets, if necessary, using nested routers.

*   Make sure OpenAPI documentation is properly rendered and annotated. New
    views and actions always require overrides (at least for the summary of
    the view). Also check you console for OpenAPI related warnings, there
    should be none.

*   Make sure every class attribute is set properly, especially permissions and
    OAuth scopes.
