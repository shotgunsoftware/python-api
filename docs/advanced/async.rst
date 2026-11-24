.. _async_client:

############
Async client
############

``AsyncShotgun`` is an asyncio client for running many requests at the same time. It sends the
same requests as :class:`~shotgun_api3.Shotgun` and returns the same results and errors, so
you can use it where the blocking client would leave your program waiting on the network.

************
Installation
************

The async client needs the `httpx <https://www.python-httpx.org/>`_ library, which is an
optional dependency::

    pip install shotgun_api3[async]

Without it, ``import shotgun_api3`` still works. Only using ``AsyncShotgun`` raises an
``ImportError`` that names the ``async`` extra.

*****
Usage
*****

Create the client with the same arguments as ``Shotgun`` and use it as an async context
manager, so its connections are closed when you are done:

.. code-block:: python

    import asyncio

    from shotgun_api3 import AsyncShotgun


    async def main():
        async with AsyncShotgun(
            "https://yoursite.shotgrid.autodesk.com",
            script_name="my_script",
            api_key="my_key",
            max_connections=10,
        ) as sg:
            # All 100 requests are in flight at once, up to max_connections at a time.
            shots = await asyncio.gather(
                *(
                    sg.find_one("Shot", [["id", "is", shot_id]], ["code"])
                    for shot_id in range(1, 101)
                )
            )
            print(len(shots), "shots")


    asyncio.run(main())

Without ``async with``, call ``await sg.close()`` when you are finished. The client opens new
connections if you use it again after closing it.

********************
Limiting concurrency
********************

``max_connections`` (default ``10``) is the most simultaneous connections to the server.
Requests beyond that wait for a free connection, so ``asyncio.gather`` over thousands of
calls does not open thousands of sockets. Raise it for more throughput, keeping in mind the
load it puts on your site.

*****************
What is available
*****************

The methods have the same names, arguments and return values as on ``Shotgun``, and are
awaited:

- Records: ``find``, ``find_one``, ``create``, ``update``, ``delete``, ``revive``, ``batch`` and
  ``summarize``.
- Schema: ``schema_read``, ``schema_entity_read``, ``schema_field_read``,
  ``schema_field_create``, ``schema_field_update`` and ``schema_field_delete``.
- Following: ``follow``, ``unfollow``, ``followers`` and ``following``.
- Notes and activity: ``note_thread_read``, ``activity_stream_read`` and ``text_search``.
- Work schedule: ``work_schedule_read`` and ``work_schedule_update``.
- Custom entities: ``custom_entity_read``, ``custom_entity_enable``,
  ``custom_entity_configure`` and ``custom_entity_disable``.
- Others: ``info``, ``preferences_read``, ``user_subscriptions_read``,
  ``user_subscriptions_create``, ``export_page``, ``nav_expand``, ``nav_search_string``,
  ``nav_search_entity``, ``connect`` and ``set_session_uuid`` (which is not awaited).

Server capabilities cannot be a blocking property in async code, so use
``await sg.get_server_caps()``. Tasks that ask at the same time share one request.

Errors are the same as the blocking client's, and so are the retries: SSL connection
errors and ``502`` or ``504`` responses are retried with the same limits and backoff, without
blocking the event loop while waiting.

*********************
What is not available
*********************

These are not supported yet:

- Uploads and downloads. ``create`` and ``update`` raise ``NotImplementedError``, before sending
  any request, when asked to upload a thumbnail or filmstrip.
- Authenticating with an ``auth_token`` (two-factor), and the methods that depend on it:
  ``get_session_token`` and ``authenticate_human_user``. The latter changes the credentials of
  the client while it runs, which is not safe with several requests in flight.
- ``update_project_last_accessed``.
- ``Mockgun``.

Calling one of these methods raises ``NotImplementedError`` right away, without making any
request, and the message names the ``Shotgun`` method to use instead. Run that from a worker
thread (``await asyncio.to_thread(...)``) if you need the event loop to stay free.
