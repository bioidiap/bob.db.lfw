.. vim: set fileencoding=utf-8 :
.. @author: Manuel Guenther <Manuel.Guenther@idiap.ch>
.. @date:   Thu Dec  6 12:28:25 CET 2012

==============
 User's Guide
==============

This package contains the access API and descriptions for the `Labeled Faced in the Wild <http://vis-www.cs.umass.edu/lfw>`_ (LFW) database.
It only contains the Bob_ accessor methods to use the DB directly from python, with our certified protocols.
The actual raw data for the database should be downloaded from the original URL (though we were not able to contact the corresponding Professor).

The Database Interface
----------------------

The :py:class:`bob.db.lfw.Database` complies with the standard biometric verification database as described in `bob.db.base <bob.db.base>`_, implementing the interface :py:class:`bob.db.base.SQLiteDatabase`.


Particularities of the LFW Database
-----------------------------------

The LFW database provides two different sets (called "views").
The first one, called ``view1`` is to be used for optimizing meta-parameters of your algorithm.
When querying the database, please use ``protocol='view1'`` to get the data only for this view.
Please note that in ``view1`` there is only a ``'dev'`` group, but no ``'eval'``.

The second view is split up into 10 different "folds".
According to http://vis-www.cs.umass.edu/lfw, in each fold 9/10 of the database are used for training, and one for evaluation.
In **this implementation** of the LFW database (:py:class:`bob.db.lfw.Database`), up to 7/10 of the data is used for training (``groups='world'``), 2/10 are used for development (to estimate a threshold; ``groups='dev'``) and the last 1/10 is finally used to evaluate the system (``groups='eval'``).
To limit the ``'world'`` set further, use one of the available ``subworld`` keywords (``'onefolds'``, ``'twofolds'``, ``'threefolds'``, ``'fourfolds'``, ``'fivefolds'``, ``'sixfolds'``, ``'sevenfolds'``) when calling the :py:meth:`bob.db.lfw.Database.objects` function.

To compute recognition results, please execute experiments on all 10 protocols (``protocol='fold1'`` ... ``protocol='fold10'``) and average the resulting classification results (cf. http://vis-www.cs.umass.edu/lfw for details on scoring).

The design of this implementation differs slightly compared to the one from http://vis-www.cs.umass.edu/lfw.
Originally, only lists of image pairs are provided by the creators of the LFW database.
To be consistent with other verification databases in Bob, here the lists are split up into files to be enrolled, and probe files.
The files to be enrolled are always the first file in the pair, while the second pair item is used as probe.

.. note::
  When querying probe files, please **always** query probe files for a specific model id: ``objects(..., purposes = 'probe', model_ids = (model_id,))``.
  In this case, you will follow the default protocols given by the database.

When querying training files ``objects(..., groups='world')``, you will automatically end up with the *image restricted configuration*.
When you want to respect the *unrestricted configuration* (cf. README on http://vis-www.cs.umass.edu/lfw), please query the files that belong to the pairs, via ``objects(..., groups='world', world_type='unrestricted')``

If you want to stick to the original protocol and use only the pairs for training and testing, feel free to query the :py:meth:`bob.db.lfw.Database.pairs` function.

.. note::
  The pairs that are provided using the :py:meth:`bob.db.lfw.Database.pairs` function, and the files provided by the :py:meth:`bob.db.lfw.Database.objects` function (see note above) correspond to the identical model/probe pairs.
  Hence, either of the two approaches should give the same recognition results.

The database comes with automatically detected annotations of several landmarks, which are provided by http://lear.inrialpes.fr/people/guillaumin/data.php.
To be consistent with our other image databases, we added the eye center coordinates ``'leye'`` and ``'reye'`` automatically by averaging between the eye corners of the according eyes.

.. warning::
  The annotations are provided for the ``funneled`` images (**not the deep funneled ones**), which can be downloaded from http://vis-www.cs.umass.edu/lfw as well.
  For the original LFW images, these annotations won't work.

.. note::
  There is also the possibility to include other annotations into the database.
  Currently, including annotations from Idiap is implemented (but they are not included in the PyPI package).


.. _bob: https://www.idiap.ch/software/bob
