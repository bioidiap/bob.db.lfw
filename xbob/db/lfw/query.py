#!/usr/bin/env python
# vim: set fileencoding=utf-8 :
# @author: Manuel Guenther <Manuel.Guenther@idiap.ch>
# @date: Thu May 24 10:41:42 CEST 2012
#
# Copyright (C) 2011-2012 Idiap Research Institute, Martigny, Switzerland
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""This module provides the Dataset interface allowing the user to query the
LFW database.
"""

from bob.db import utils
from .models import *
from sqlalchemy.orm import aliased
from .driver import Interface

INFO = Interface()

SQLITE_FILE = INFO.files()[0]

class Database(object):
  """The dataset class opens and maintains a connection opened to the Database.

  It provides many different ways to probe for the characteristics of the data
  and for the data itself inside the database.
  """

  def __init__(self):
    # opens a session to the database - keep it open until the end
    self.connect()
    self.m_valid_protocols = ('view1', 'fold1', 'fold2', 'fold3', 'fold4', 'fold5', 'fold6', 'fold7', 'fold8', 'fold9', 'fold10')
    self.m_valid_groups = ('world', 'dev', 'eval')
    self.m_valid_purposes = ('enrol', 'probe')
    self.m_valid_classes = ('matched', 'unmatched')
    self.m_subworld_counts = {'onefolds':1, 'twofolds':2, 'threefolds':3, 'fourfolds':4, 'fivefolds':5, 'sixfolds':6, 'sevenfolds':7}
    self.m_valid_types = ('restricted', 'unrestricted')

  def connect(self):
    """Tries connecting or re-connecting to the database"""
    if not os.path.exists(SQLITE_FILE):
      self.m_session = None

    else:
      self.m_session = utils.session_try_readonly(INFO.type(), SQLITE_FILE)

  def is_valid(self):
    """Returns if a valid session has been opened for reading the database"""

    return self.m_session is not None

  def assert_validity(self):
    """Raise a RuntimeError if the database backend is not available"""

    if not self.is_valid():
      raise RuntimeError ("Database '%s' cannot be found at expected location '%s'. Create it and then try re-connecting using Database.connect()" % (INFO.name(), SQLITE_FILE))


  def __check_single__(self, value, description, valid):
    if not isinstance(value, str):
      raise ValueError("The given %s '%s' has to be of type 'str'" % (description, value))
    if not value in valid:
      raise ValueError("The given %s '%s' need to be one of %s" %(description, value, valid) )

  def __check_validity__(self, list, description, valid):
    """Checks validity of user input data against a set of valid values"""
    if not list: return valid
    elif isinstance(list, str): return self.__check_validity__((list,), description, valid)
    for k in list:
      if k not in valid:
        raise RuntimeError, 'Invalid %s "%s". Valid values are %s, or lists/tuples of those' % (description, k, valid)
    return list

  def __eval__(self, fold):
    return int(fold[4:])

  def __dev__(self, eval):
    # take the two parts of the training set (the ones before the eval set) for dev
    return ((eval + 7) % 10 + 1, (eval + 8) % 10 + 1)

  def __dev_for__(self, fold):
    return ["fold%d"%f for f in self.__dev__(self.__eval__(fold))]

  def __world_for__(self, fold, subworld):
    # the training sets for each fold are composed of all folds
    # except the given one and the previous
    eval = self.__eval__(fold)
    dev = self.__dev__(eval)
    world_count = self.m_subworld_counts[subworld]
    world = []
    for i in range(world_count):
      world.append((eval + i) % 10 + 1)
    return ["fold%d"%f for f in world]


  def clients(self, protocol=None, groups=None, subworld='sevenfolds'):
    """Returns a list of Client objects for the specific query by the user.

    Keyword Parameters:

    protocol
      The protocol to consider; one of: ('view1', 'fold1', ..., 'fold10')

    groups
      The groups to which the clients belong; one or several of: ('world', 'dev', 'eval')
      Note: the 'eval' group does not exist for protocol 'view1'.

    subworld
      The subset of the training data. Has to be specified if groups includes 'world'
      and protocol is one of 'fold1', ..., 'fold10'.
      It might be exactly one of ('onefolds', 'twofolds', ..., 'sevenfolds').

    Returns: A list containing all Client objects which have the desired properties.
    """
    self.assert_validity()

    self.__check_single__(protocol, 'protocol', self.m_valid_protocols)
    groups = self.__check_validity__(groups, 'group', self.m_valid_groups)
    if subworld != None:
      self.__check_single__(subworld, 'sub-world', self.m_subworld_counts.keys())

    queries = []

    # List of the clients
    if protocol == 'view1':
      if 'world' in groups:
        queries.append(\
            self.m_session.query(Client).join(File).join(People).\
                  filter(People.protocol == 'train').\
                  order_by(Client.id))
      if 'dev' in groups:
        queries.append(\
            self.m_session.query(Client).join(File).join(People).\
                  filter(People.protocol == 'test').\
                  order_by(Client.id))
    else:
      if 'world' in groups:
        # select training set for the given fold
        trainset = self.__world_for__(protocol, subworld)
        queries.append(\
            self.m_session.query(Client).join(File).join(People).\
                  filter(People.protocol.in_(trainset)).\
                  order_by(Client.id))
      if 'dev' in groups:
        # select development set for the given fold
        devset = self.__dev_for__(protocol)
        queries.append(\
            self.m_session.query(Client).join(File).join(People).\
                  filter(People.protocol.in_(devset)).\
                  order_by(Client.id))
      if 'eval' in groups:
        queries.append(\
            self.m_session.query(Client).join(File).join(People).\
                  filter(People.protocol == protocol).\
                  order_by(Client.id))

    # all queries are made; now collect the clients
    retval = []
    for query in queries:
      for client in query:
        retval.append(client)

    return retval


  def models(self, protocol=None, groups=None, subworld='sevenfolds'):
    """Returns a list of File objects (there are multiple models per client) for the specific query by the user.
    Note that for 'world' sets in the 'restricted' case, both images of the pairs are returned,
    while for the 'dev' and 'eval' groups, only the first element of the pair is extracted.

    Keyword Parameters:

    protocol
      The protocol to consider; one of: ('view1', 'fold1', ..., 'fold10')

    groups
      The groups to which the clients belong; one or several of: ('world', 'dev', 'eval')
      The 'eval' group does not exist for protocol 'view1'.

    subworld
      The subset of the training data. Has to be specified if groups includes 'world'
      and protocol is one of 'fold1', ..., 'fold10'.
      It might be exactly one of ('onefolds', 'twofolds', ..., 'sevenfolds').

    Returns: A list containing all File objects which have the desired properties.
    """

    self.assert_validity()

    self.__check_single__(protocol, 'protocol', self.m_valid_protocols)
    groups = self.__check_validity__(groups, 'group', self.m_valid_groups)
    if subworld != None:
      self.__check_single__(subworld, 'sub-world', self.m_subworld_counts.keys())

    # the restricted case...
    queries = []

    # List of the models
    if protocol == 'view1':
      if 'world' in groups:
        queries.append(\
            self.m_session.query(File).join((Pair, or_(File.id == Pair.enrol_file_id, File.id == Pair.probe_file_id))).\
                  filter(Pair.protocol == 'train'))
      if 'dev' in groups:
        queries.append(\
            # enroll files
            self.m_session.query(File).join((Pair, File.id == Pair.enrol_file_id)).\
                  filter(Pair.protocol == 'test'))
    else:
      if 'world' in groups:
        # select training set for the given fold
        trainset = self.__world_for__(protocol, subworld)
        queries.append(\
            self.m_session.query(File).join((Pair, or_(File.id == Pair.enrol_file_id, File.id == Pair.probe_file_id))).\
                  filter(Pair.protocol.in_(trainset)))
      if 'dev' in groups:
        # select development set for the given fold
        devset = self.__dev_for__(protocol)
        queries.append(\
            self.m_session.query(File).join((Pair, File.id == Pair.enrol_file_id)).\
                  filter(Pair.protocol.in_(devset)))
      if 'eval' in groups:
        queries.append(\
            self.m_session.query(File).join((Pair, File.id == Pair.enrol_file_id)).\
                  filter(Pair.protocol == protocol))

    # all queries are made; now collect the files
    retval = []
    for query in queries:
      retval.extend([file for file in query])

    return retval


  def get_client_id_from_file_id(self, file_id):
    """Returns the client_id (real client id) attached to the given file_id

    Keyword Parameters:

    file_id
      The file_id to consider

    Returns: The client_id attached to the given file_id
    """
    self.assert_validity()

    q = self.m_session.query(File).\
          filter(File.id == file_id)

    assert q.count() == 1
    return q.first().client_id


  def get_client_id_from_model_id(self, model_id):
    """Returns the client_id (real client id) attached to the given model id

    Keyword Parameters:

    model_id
      The model to consider

    type
      One of ('restricted', 'unrestricted'). If the type 'restricted' is given,
      model_ids will be handled as file ids, if type is 'unrestricted', model ids
      will be client ids.

    Returns: The client_id attached to the given model
    """

    # since there is one model per file, we can re-use the function above.
    return self.get_client_id_from_file_id(model_id)



  def objects(self, protocol=None, model_ids=None, groups=None, purposes=None, subworld='sevenfolds', world_type='restricted'):
    """Returns a list of File objects for the specific query by the user.

    Keyword Parameters:

    protocol
      The protocol to consider ('view1', 'fold1', ..., 'fold10')

    groups
      The groups to which the objects belong ('world', 'dev', 'eval')

    purposes
      The purposes of the objects ('enrol', 'probe')

    subworld
      The subset of the training data. Has to be specified if groups includes 'world'
      and protocol is one of 'fold1', ..., 'fold10'.
      It might be exactly one of ('onefolds', 'twofolds', ..., 'sevenfolds').

    world_type
      One of ('restricted', 'unrestricted'). If 'restricted', only the files that
      are used in one of the training pairs are used. For 'unrestricted', all
      files of the training people are returned.

    model_ids
      Only retrieves the objects for the provided list of model ids.
      If 'None' is given (this is the default), no filter over the model_ids is performed.
      Note that the combination of 'world' group and 'model_ids' should be avoided.

    Returns: A list of File objects considering all the filtering criteria.
    """

    self.assert_validity()

    self.__check_single__(protocol, "protocol", self.m_valid_protocols)
    groups = self.__check_validity__(groups, "group", self.m_valid_groups)
    purposes = self.__check_validity__(purposes, "purpose", self.m_valid_purposes)
    self.__check_single__(world_type, 'training type', self.m_valid_types)

    if subworld != None:
      self.__check_single__(subworld, 'sub-world', self.m_subworld_counts.keys())

    if(isinstance(model_ids,str)):
      model_ids = (model_ids,)

    queries = []
    probe_queries = []
    file_alias = aliased(File)

    if protocol == 'view1':
      if 'world' in groups:
        # training files of view1
        if world_type == 'restricted':
          queries.append(\
              self.m_session.query(File).join((Pair, or_(File.id == Pair.enrol_file_id, File.id == Pair.probe_file_id))).\
                  filter(Pair.protocol == 'train'))
        else:
          queries.append(\
              self.m_session.query(File).join(People).\
                  filter(People.protocol == 'train'))
      if 'dev' in groups:
        # test files of view1
        if 'enrol' in purposes:
          queries.append(\
              self.m_session.query(File).join((Pair, File.id == Pair.enrol_file_id)).\
                  filter(Pair.protocol == 'test'))
        if 'probe' in purposes:
          probe_queries.append(\
              self.m_session.query(File).\
                  join((Pair, File.id == Pair.probe_file_id)).\
                  join((file_alias, Pair.enrol_file_id == file_alias.id)).\
                  filter(Pair.protocol == 'test'))

    else:
      # view 2
      if 'world' in groups:
        # world set of current fold of view 2
        trainset = self.__world_for__(protocol, subworld)
        if world_type == 'restricted':
          queries.append(\
              self.m_session.query(File).join((Pair, or_(File.id == Pair.enrol_file_id, File.id == Pair.probe_file_id))).\
                  filter(Pair.protocol.in_(trainset)))
        else:
          queries.append(\
              self.m_session.query(File).join(People).\
                  filter(People.protocol.in_(trainset)))

      if 'dev' in groups:
        # development set of current fold of view 2
        devset = self.__dev_for__(protocol)
        if 'enrol' in purposes:
          queries.append(\
              self.m_session.query(File).join((Pair, File.id == Pair.enrol_file_id)).\
                  filter(Pair.protocol.in_(devset)))
        if 'probe' in purposes:
          probe_queries.append(\
              self.m_session.query(File).\
                  join((Pair, File.id == Pair.probe_file_id)).\
                  join((file_alias, file_alias.id == Pair.enrol_file_id)).\
                  filter(Pair.protocol.in_(devset)))

      if 'eval' in groups:
        # evaluation set of current fold of view 2; this is the REAL fold
        if 'enrol' in purposes:
          queries.append(\
              self.m_session.query(File).join((Pair, File.id == Pair.enrol_file_id)).\
                  filter(Pair.protocol == protocol))
        if 'probe' in purposes:
          probe_queries.append(\
              self.m_session.query(File).\
                  join((Pair, File.id == Pair.probe_file_id)).\
                  join((file_alias, file_alias.id == Pair.enrol_file_id)).\
                  filter(Pair.protocol == protocol))

    retval = []
    for query in queries:
      if model_ids and len(model_ids):
        query = query.filter(File.id.in_(model_ids))

      retval.extend([file for file in query])

    for query in probe_queries:
      if model_ids and len(model_ids):
        query = query.filter(file_alias.id.in_(model_ids))

      for probe in query:
        retval.append(probe)

    return retval


  def pairs(self, protocol=None, groups=None, classes=None, subworld='sevenfolds'):
    """Queries a list of Pair's of files.

    Keyword Parameters:

    protocol
      The protocol to consider ('view1', 'fold1', ..., 'fold10')

    groups
      The groups to which the objects belong ('world', 'dev', 'eval')

    classes
      The classes to which the pairs belong ('matched', 'unmatched')

    subworld
      The subset of the training data. Has to be specified if groups includes 'world'
      and protocol is one of 'fold1', ..., 'fold10'.
      It might be exactly one of ('onefolds', 'twofolds', ..., 'sevenfolds').

    Returns: A list of Pair's considering all the filtering criteria.
    """

    def default_query():
      return self.m_session.query(Pair).\
                join(File1, File1.id == Pair.enrol_file_id).\
                join(File2, File2.id == Pair.probe_file_id)

    self.assert_validity()

    self.__check_single__(protocol, "protocol", self.m_valid_protocols)
    groups = self.__check_validity__(groups, "group", self.m_valid_groups)
    classes = self.__check_validity__(classes, "class", self.m_valid_classes)
    if subworld != None:
      self.__check_single__(subworld, 'sub-world', self.m_subworld_counts.keys())

    queries = []
    File1 = aliased(File)
    File2 = aliased(File)

    if protocol == 'view1':
      if 'world' in groups:
        queries.append(default_query().filter(Pair.protocol == 'train'))
      if 'dev' in groups:
        queries.append(default_query().filter(Pair.protocol == 'test'))

    else:
      if 'world' in groups:
        trainset = self.__world_for__(protocol, subworld)
        queries.append(default_query().filter(Pair.protocol.in_(trainset)))
      if 'dev' in groups:
        devset = self.__dev_for__(protocol)
        queries.append(default_query().filter(Pair.protocol.in_(devset)))
      if 'eval' in groups:
        queries.append(default_query().filter(Pair.protocol == protocol))

    retval = []
    for query in queries:
      if not 'matched' in classes:
        query = query.filter(Pair.is_match == False)
      if not 'unmatched' in classes:
        query = query.filter(Pair.is_match == True)

      for pair in query:
        retval.append(pair)

    return retval


  def paths(self, file_ids, prefix='', suffix=''):
    """Returns a full file paths considering particular file ids, a given
    directory and an extension.

    Keyword Parameters:

    file_ids
      The ids of the object in the database table "file". This object should be
      a python iterable (such as a tuple or list).

    prefix
      The bit of path to be prepended to the filename stem

    suffix
      The extension determines the suffix that will be appended to the filename
      stem.

    Returns a list (that may be empty) of the fully constructed paths given the
    file ids.
    """

    self.assert_validity()

    queried_files = self.session.query(File).filter(File.id.in_(file_ids))
    retval = []
    for id in file_ids:
      retval.extend([file.make_path(prefix, suffix) for file in queried_files if file.id == id])
    return retval


  def reverse(self, paths):
    """Reverses the lookup: from certain stems, returning file ids

    Keyword Parameters:

    paths
      The filename stems I'll query for. This object should be a python
      iterable (such as a tuple or list)

    Returns a list (that may be empty).
    """

    self.assert_validity()

    retval = []
    queried_files = self.session.query(File).filter(File.path.in_(paths))
    for path in paths:
      retval.extend([file.id for file in queried_files if file.path == path])
    return retval



