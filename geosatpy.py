# -*- coding: utf-8 -*-
"""
@author: Maximilien Houel
"""

import os
import numpy as np
import gdal
import osgeo.ogr
import utm
import mgrs

class GetGeoInfo:
    def vector(self,path) :
        """
        
        Parameters
        ----------
        path : str
            path to the vector file (format .shp / .geojson ...).

        Returns
        -------
        infos : dict
            Dictionnary with Extent / fields + values of each feature.

        """
        file = osgeo.ogr.Open(path, 1)
        layer = file.GetLayer()
        layerDfn = layer.GetLayerDefn()
        fields = []
        for i in range(layerDfn.GetFieldCount()):
            fields.append(layerDfn.GetFieldDefn(i).GetName())
        infos = {}
        f = 0 
        for feature in layer :
            geom = feature.GetGeometryRef()
            wkt = geom.ExportToWkt()
            geoJson = geom.ExportToJson()
            tmp={'WKT':wkt,
                 'JSON' : geoJson}
            for field in fields :
                tmp.update({field:feature.GetField(field)})
            infos.update({f:tmp})
            f+=1
        return infos
    
    def raster(self,path) :
        """
        
        Parameters
        ----------
        path : str
            DESCRIPTION.

        Returns
        -------
        dict
            Dictionnary with raster info : projection, Full Geometry, 
            number of Bands, x and y Resolution, Width and Height of the array.

        """
        data = gdal.Open(path)
        prj = data.GetProjection()
        geo = data.GetGeoTransform()
        nBands = data.RasterCount    
        xres = geo[1]
        yres = geo[5]
        shape = data.ReadAsArray().shape
        return {'Projection' : prj,
                'Geometry' : geo,
                'nBands' : nBands,
                'xRes' : xres,
                'yRes' : yres,
                'Width' : shape[-1:][0],
                'Height' : shape[-2:][0]}
    
class GeoProcess:
    def asArray(self,path, band = None):
        """

        Parameters
        ----------
        path : str
            path to the raster file to open
        band : int, optional
            Integer to open a specific band. The default is None.

        Returns
        -------
        TYPE array
            Return the array of the raster file opened.

        """
        data = gdal.Open(path,gdal.GA_ReadOnly)
        if data is not None :
            num_bands = data.RasterCount
            if band is None :
                if num_bands > 1 :
                    array = data.ReadAsArray()
                    array = np.dstack(array)
                else :
                    array = data.ReadAsArray()
            else :
                b = data.GetRasterBand(band)
                array = b.ReadAsArray()
            return array
        
        else :
            return print('No data in {}'.format(path))       

    def buildVRT(self,list_files, dst) :
        """

        Parameters
        ----------
        list_files : list of str
            List of file to compile.
        dst : str
            Path to the .vrt file to save.

        Returns
        -------
        Saving at dst.

        """
        gdal.BuildVRT(destName = dst,
                      srcDSOrSrcDSTab = list_files,
                      allowProjectionDifference = True)
        
    def vrtToTiff(self,vrtFile, dst) :
        """

        Parameters
        ----------
        vrtFile : str
            path to a .vrt file.
        dst : str
            Path to the .tif file to save.

        Returns
        -------
        Saving at dst.

        """
        gdal.Translate(destName = dst,
                       srcDS = vrtFile,
                       format = 'GTiff')
        
    def merge(self,list_files, vrt, dst) :
        """

        Parameters
        ----------
        list_files : list of str
            List of files to combine in one.
        vrt : str
            Path to the tmp vrt file.
        dst : str
            Path to the destionation tif.

        Returns
        -------
        Saving .tif file combining files in the list
        Delete temporary .vrt file.
        """
        GeoProcess.buildVRT(list_files, vrt)
        GeoProcess.vrtToTiff(vrt, dst)
        os.remove(vrt)
        
    def tiling(self,src, dst, size_w, size_h, dtype = 'Float32', noData = None) :
        """
        
        Parameters
        ----------
        src : str
            Path to the file to tile.
        dst : str
            Path to the tiles. (Automatically the script add
                                additional number of tile
            ex : dst = tile -> output = tile_{n}.tif
        size_w : int
            width size of the tile.
        size_h : int
            height size of the tile.
        dtype : str, optional
            Radiometric resolution : Float32 / Float64 / UInt16 / Byte
                . The default is 'Float32'.
        noData : int, optional
            Set a specific value for the nan data
            . The default is None.

        Returns
        -------
        Saved tiles at dst.

        """
        tile = 0
        im = GeoProcess.asArray(src)
        if dtype == 'Float32':
            outputType = gdal.GDT_Float32
        if dtype == 'Float64':
            outputType = gdal.GDT_Float64
        if dtype == 'UInt16':
            outputType = gdal.GDT_UInt16 
        if dtype == 'Byte':
            outputType = gdal.GDT_Byte
        if len(im.shape) > 2 :
            h, w, bands =  im.shape
        else :
            h, w = im.shape
            
        for i in range(0,w, size_w):
            for j in range(0, h, size_h):
                tile += 1
                destName = dst + '_{}.tif'.format(tile)
                if not os.path.isfile(destName):
                    gdal.Translate(destName = destName,
                                   srcDS = src,
                                   format = 'GTiff',
                                   outputType = outputType,
                                   srcWin = [i, j, size_w, size_h],
                                   noData = noData)         
    
    def resizing(self,src, dst, width = None, height = None, xRes = None, yRes = None, dtype = 'Float32') :
        """
        Resizing process can be choose with shape size or pixel resolution
        
        Parameters
        ----------
        src : str
            Path to the file to resize.
        dst : str
            Output path.
        width : int, optional
            Width size for resizing
            . The default is None.
        height : int, optional
            Height size for resizing
            . The default is None.
        xRes : int, optional
            x resolution for resizing
            . The default is None.
        yRes : int, optional
            y resolution for resizing
            . The default is None.
        dtype : str, optional
            Radiometric resolution : Float32 / Float64 / UInt16 / Byte
            . The default is 'Float32'.

        Returns
        -------
        Resized file at dst.

        """
        if dtype == 'Float32':
            outputType = gdal.GDT_Float32
        if dtype == 'Float64':
            outputType = gdal.GDT_Float64
        if dtype == 'UInt16':
            outputType = gdal.GDT_UInt16 
        if dtype == 'Byte':
            outputType = gdal.GDT_Byte
        if xRes is None :
            if yRes is None :
                print('New size : width = {} / height = {}'.format(width, height))
                gdal.Warp(dst,
                          src,
                          width = width,
                          height = height,
                          outputType = outputType,
                          resampleAlg = 3)
        if width is None :
            if height is None :
                print('New resolution : xRes = {} / yRes = {}'.format(xRes, yRes))
                gdal.Warp(dst,
                          src,
                          xRes = xRes,
                          yRes = yRes,
                          outputType = outputType,
                          resampleAlg = 3)
    
    
    def crop(self,src, dst, vec, dtype = 'Float32') :
        """

        Parameters
        ----------
        src : str
            Path to file to crop.
        dst : str
            Output path.
        vec : str
            Path to the vector file for cropping.
        dtype : str, optional
            Radiometric resolution : Float32 / Float64 / UInt16 / Byte
            . The default is 'Float32'.

        Returns
        -------
        Crop file at dst

        """
        if dtype == 'Float32':
            outputType = gdal.GDT_Float32
        if dtype == 'Float64':
            outputType = gdal.GDT_Float64
        if dtype == 'UInt16':
            outputType = gdal.GDT_UInt16 
        if dtype == 'Byte':
            outputType = gdal.GDT_Byte
        gdal.Warp(dst,
                  src,
                  format = 'GTiff',
                  cutlineDSName = vec,
                  outputType = outputType,
                  cropToCutline = True,
                  resampleAlg = 3)
     
    def save_tiff(self,dst_filename, nparray, ref_proj, ref_geom, dtype = 'Float32', nodata_value =-9999.9): 
        """

        Parameters
        ----------
        dst_filename : str
            Path for the saving output.
        nparray : narray
            Array to save.
        ref_proj : str
            Path to the referenced file for projection.
        ref_geom : str
            Path to the referenced file for geometry.
        dtype : str, optional
            Radiometric resolution : Float32 / Float64 / UInt16 / Byte
            . The default is 'Float32'.
        nodata_value : int, optional
            Set a specific value for the nan data
            . The default is -9999.

        Returns
        -------
        Saved array at dst_filename.

        """
        proj_ref = gdal.Open(ref_proj, gdal.GA_ReadOnly)
        geom_ref = gdal.Open(ref_geom, gdal.GA_ReadOnly)
        if len(nparray.shape) == 2 :
            [cols, rows] = nparray.shape
            bands = 1
        else :
            [cols, rows, bands] = nparray.shape
        if dtype == 'Float32':
            outputType = gdal.GDT_Float32
        if dtype == 'Float64':
            outputType = gdal.GDT_Float64
        if dtype == 'UInt16':
            outputType = gdal.GDT_UInt16 
        if dtype == 'Byte':
            outputType = gdal.GDT_Byte
        outdata = gdal.GetDriverByName("GTiff").Create(str(dst_filename),rows, cols, bands, outputType)
        outdata.SetGeoTransform(geom_ref.GetGeoTransform())
        outdata.SetProjection(proj_ref.GetProjectionRef())
        if bands > 1 :
            for band in range(1, bands + 1) :
                outdata.GetRasterBand(band).SetNoDataValue(nodata_value)
                outdata.GetRasterBand(band).WriteArray(nparray[:,:,band-1])
        else :
            outdata.GetRasterBand(bands).SetNoDataValue(nodata_value)
            outdata.GetRasterBand(bands).WriteArray(nparray)
        outdata.FlushCache()     

class CoordConverter :
    def getTile(self,lat, long) :
        """

        Parameters
        ----------
        lat : int
            Latitude to convert.
        long : int
            Longitude to convert.

        Returns
        -------
        tile : str
            Give corresponding MGRS tile from lat / long input.

        """
        m = mgrs.MGRS()
        c=m.toMGRS(lat,long)
        c = c.decode('utf-8')
        tile = 'T' + c[:5]
        return tile
    def wgsTOutm(self,lat,long):
        """

        Parameters
        ----------
        lat : int
            Latitude to convert.
        long : int
            Longitude to convert.

        Returns
        -------
        zone : str
            UTM conversion corresponding to lat / long input.

        """
        utm_coords = utm.from_latlon(lat,long)
        return utm_coords

    
    
    
    
    
    
    
