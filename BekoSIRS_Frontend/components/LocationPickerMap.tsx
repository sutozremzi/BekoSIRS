import React, { useMemo, useRef, useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { WebView } from 'react-native-webview';
import * as Location from 'expo-location';
import { FontAwesome } from '@expo/vector-icons';
import { t } from '../i18n';

interface Props {
  latitude: number | null;
  longitude: number | null;
  onChange: (lat: number, lng: number) => void;
}

// KKTC / Lefkoşa varsayılan merkez
const DEFAULT_LAT = 35.1856;
const DEFAULT_LNG = 33.3823;

const buildHtml = (lat: number, lng: number, hasMarker: boolean) => `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>html, body, #map { height: 100%; margin: 0; padding: 0; } </style>
</head>
<body>
  <div id="map"></div>
  <script>
    var map = L.map('map').setView([${lat}, ${lng}], ${hasMarker ? 15 : 12});
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© OpenStreetMap'
    }).addTo(map);

    var marker = ${hasMarker ? `L.marker([${lat}, ${lng}], { draggable: true }).addTo(map)` : 'null'};

    function post(la, ln) {
      if (window.ReactNativeWebView) {
        window.ReactNativeWebView.postMessage(JSON.stringify({ type: 'select', lat: la, lng: ln }));
      }
    }
    function onDrag() {
      var p = marker.getLatLng();
      post(p.lat, p.lng);
    }
    function placeMarker(la, ln) {
      if (!marker) {
        marker = L.marker([la, ln], { draggable: true }).addTo(map);
        marker.on('dragend', onDrag);
      } else {
        marker.setLatLng([la, ln]);
      }
    }
    if (marker) { marker.on('dragend', onDrag); }

    map.on('click', function (e) {
      placeMarker(e.latlng.lat, e.latlng.lng);
      post(e.latlng.lat, e.latlng.lng);
    });

    // RN tarafından "Konumumu Kullan" sonrası çağrılır
    window.setMarker = function (la, ln) {
      placeMarker(la, ln);
      map.setView([la, ln], 16);
    };
  </script>
</body>
</html>`;

export default function LocationPickerMap({ latitude, longitude, onChange }: Props) {
  const webRef = useRef<WebView>(null);
  const [locating, setLocating] = useState(false);
  const [loaded, setLoaded] = useState(false);

  const hasMarker = latitude != null && longitude != null;
  const initLat = latitude ?? DEFAULT_LAT;
  const initLng = longitude ?? DEFAULT_LNG;

  // html'i yalnızca ilk render'da kur; sonraki marker güncellemeleri injectJavaScript ile yapılır
  const html = useMemo(() => buildHtml(initLat, initLng, hasMarker), []);

  const handleMessage = (event: any) => {
    try {
      const data = JSON.parse(event.nativeEvent.data);
      if (data.type === 'select' && typeof data.lat === 'number' && typeof data.lng === 'number') {
        onChange(data.lat, data.lng);
      }
    } catch {
      // yok say
    }
  };

  const useMyLocation = async () => {
    try {
      setLocating(true);
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('', t('profile.locationPermissionDenied'));
        return;
      }
      const pos = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
      const { latitude: la, longitude: ln } = pos.coords;
      onChange(la, ln);
      webRef.current?.injectJavaScript(`window.setMarker(${la}, ${ln}); true;`);
    } catch {
      Alert.alert('', t('profile.locationError'));
    } finally {
      setLocating(false);
    }
  };

  return (
    <View style={{ flex: 1 }}>
      <WebView
        ref={webRef}
        originWhitelist={['*']}
        source={{ html }}
        onMessage={handleMessage}
        onLoadEnd={() => setLoaded(true)}
        javaScriptEnabled
        domStorageEnabled
        style={{ flex: 1 }}
      />
      {!loaded && (
        <View style={styles.loadingOverlay}>
          <ActivityIndicator size="large" color="#0066cc" />
          <Text style={styles.loadingText}>{t('profile.mapLoading')}</Text>
        </View>
      )}
      <TouchableOpacity
        style={styles.gpsButton}
        onPress={useMyLocation}
        disabled={locating}
        activeOpacity={0.8}
      >
        {locating ? (
          <ActivityIndicator color="#fff" size="small" />
        ) : (
          <FontAwesome name="location-arrow" size={16} color="#fff" />
        )}
        <Text style={styles.gpsButtonText}>
          {locating ? t('profile.locating') : t('profile.useMyLocation')}
        </Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  loadingOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: '#fff',
    alignItems: 'center',
    justifyContent: 'center',
  },
  loadingText: {
    marginTop: 10,
    color: '#666',
    fontSize: 14,
  },
  gpsButton: {
    position: 'absolute',
    bottom: 20,
    alignSelf: 'center',
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#0066cc',
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderRadius: 25,
    gap: 8,
    elevation: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 4,
  },
  gpsButtonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 14,
  },
});
