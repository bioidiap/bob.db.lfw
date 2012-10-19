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

"""Table models and functionality for the LFW database.
"""

import sqlalchemy
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, or_, and_, not_
from bob.db.sqlalchemy_migration import Enum, relationship
from sqlalchemy.orm import backref
from sqlalchemy.ext.declarative import declarative_base

import os
import bob

Base = declarative_base()

class Client(Base):
  """Information about the clients (identities) of the LFW database."""
  __tablename__ = 'client'

  id = Column(String(100), primary_key=True)

  def __init__(self, name):
    self.id = name

  def __repr__(self):
    return "<Client('%s')>" % self.id

class File(Base):
  """Information about the files of the LFW database."""
  __tablename__ = 'file'

  # Unique key identifier for the file; here we use strings
  id = Column(String(100), primary_key=True)
  # Identifier for the client
  client_id = Column(String(100), ForeignKey('client.id'))
  # Unique path to this file inside the database
  path = Column(String(100))
  # Identifier for the current image number of the client
  shot_id = Column(Integer)

  # a back-reference from file to client
  client = relationship("Client", backref=backref("files", order_by=id))

  def __init__(self, client_id, shot_id):
    self.client_id = client_id
    self.shot_id = shot_id
    self.id = client_id + "_" + "0"*(4-len(str(shot_id))) + str(shot_id)
    self.path = os.path.join(client_id, self.id)

  def __repr__(self):
    print "<File('%s')>" % os.path.join(self.client_id, self.id)

  def make_path(self, directory=None, extension=None):
    """Wraps the current path so that a complete path is formed

    Keyword parameters:

    directory
      An optional directory name that will be prefixed to the returned result.

    extension
      An optional extension that will be suffixed to the returned filename. The
      extension normally includes the leading ``.`` character as in ``.jpg`` or
      ``.hdf5``.

    Returns a string containing the newly generated file path.
    """

    if not directory: directory = ''
    if not extension: extension = ''

    return os.path.join(directory, self.path + extension)

  def save(self, data, directory=None, extension='.hdf5'):
    """Saves the input data at the specified location and using the given
    extension.

    Keyword parameters:

    data
      The data blob to be saved (normally a :py:class:`numpy.ndarray`).

    directory
      If not empty or None, this directory is prefixed to the final file
      destination

    extension
      The extension of the filename - this will control the type of output and
      the codec for saving the input blob.
    """

    path = self.make_path(directory, extension)
    bob.utils.makedirs_safe(os.path.dirname(path))
    bob.io.save(data, path)


class People(Base):
  """Information about the people (as given in the people.txt file) of the LFW database."""
  __tablename__ = 'people'

  id = Column(Integer, primary_key=True)
  protocol = Column(Enum('train', 'test', 'fold1', 'fold2', 'fold3', 'fold4', 'fold5', 'fold6', 'fold7', 'fold8', 'fold9', 'fold10'))
  file_id = Column(String(100), ForeignKey('file.id'))

  def __init__(self, protocol, file_id):
    self.protocol = protocol
    self.file_id = file_id

  def __repr__(self):
    return "<People('%s', '%s')>" % (self.protocol, self.file_id)

class Pair(Base):
  """Information of the pairs (as given in the pairs.txt files) of the LFW database."""
  __tablename__ = 'pair'

  id = Column(Integer, primary_key=True)
  # train and test for view1, the folds for view2
  protocol = Column(Enum('train', 'test', 'fold1', 'fold2', 'fold3', 'fold4', 'fold5', 'fold6', 'fold7', 'fold8', 'fold9', 'fold10'))
  enrol_file_id = Column(String(100), ForeignKey('file.id'))
  probe_file_id = Column(String(100), ForeignKey('file.id'))
  enrol_file = relationship("File", backref=backref("enrol_files", order_by=id), primaryjoin="Pair.enrol_file_id==File.id")
  probe_file = relationship("File", backref=backref("probe_files", order_by=id), primaryjoin="Pair.probe_file_id==File.id")
  is_match = Column(Boolean)

  def __init__(self, protocol, enrol_file_id, probe_file_id, is_match):
    self.protocol = protocol
    self.enrol_file_id = enrol_file_id
    self.probe_file_id = probe_file_id
    self.is_match = is_match

  def __repr__(self):
    return "<Pair('%s', '%s', '%s', '%d')>" % (self.protocol, self.enrol_file_id, self.probe_file_id, 1 if self.is_match else 0)

