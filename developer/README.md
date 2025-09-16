
# Updating HTTPLib2

The API comes with a copy of the `httplib2` inside the `shotgun_api3/lib` folder. To update the copy to a more recent version of the API, you can run the `update_httplib2.py` script at the root of this repository like this:

    python update_httplib2.py vX.Y.Z

where `vX.Y.Z` is a release found on `httplib2`'s [release page](https://github.com/httplib2/httplib2/releases).


# Release process

## Packaging up new release

1) Update the Changelog in the `HISTORY.rst` file
    - Add bullet points for any changes that have happened since the previous release. This may include changes you did not make so look at the commit history and make sure we don't miss anything. If you notice something was done that wasn't added to the changelog, hunt down that engineer and make them feel guilty for not doing so. This is a required step in making changes to the API.
    - Try and match the language of previous change log messages. We want to keep a consistent voice.
    - Make sure the date of the release matches today. We try and keep this TBD until we're ready to do a release so it's easy to catch that it needs to be updated.
    - Make sure the version number is filled out and correct. We follow semantic versioning.
2) Ensure any changes or additions to public methods are documented
    - Ensure that doc strings are updated in the code itself to work with Sphinx and are correctly formatted.
    - Examples are always good especially if this a new feature or method.
    - Think about a new user to the API trying to figure out how to use the features you're documenting.
3) Update the version value in `python-api/setup.py`  to match the version you are packaging. This controls what version users will get when installing via pip.
4) Update the `__version__` value in `shotgun_api3/shotgun.py` to the version you're releasing. This identifies the current version within the API itself.
5) Commit these changes in master with a commit message like `packaging for the vx.x.x release`.
6) Create a tag based off of the master branch called `vx.x.x` to match the version number you're releasing.
7) Push master and your tag to Github.
8) Update the Releases page with your new release.
    - The release should already be there from your tag but if not, create a new one.
    - Add more detailed information regarding the changes in this release. This is a great place to add examples, and reasons for the change!

## Letting the world know
Post a message in the [Pipeline Community channel](https://community.shotgridsoftware.com/c/pipeline).

## Prepare for the Next Dev Cycle
1) Update the `__version__` value in `shotgun_api3/shotgun.py` to the next version number with `.dev` appended to it. For example, `v3.0.24.dev`
2) Add a new section to the Changelog in the `HISTORY.rst` file with the next version number and a TBD date
```
    **v3.0.24 - TBD**
       + TBD
```
3) Commit the changes to master with a commit message like `Bump version to v3.0.24.dev`
4) Push master to Github
