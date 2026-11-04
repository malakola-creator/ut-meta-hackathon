package com.utmeta.teach;

import android.Manifest;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.net.http.SslError;
import android.os.Bundle;
import android.webkit.PermissionRequest;
import android.webkit.SslErrorHandler;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

/**
 * Point and say on the headset: one full-screen WebView on the teach page (tools/teach_server.py).
 * The page's microphone request is granted once Android has given the app RECORD_AUDIO.
 * The teach server's certificate is self-signed, so it is accepted for that server's host only; every other host keeps the normal check.
 * The URL can be changed at launch: adb shell am start -n com.utmeta.teach/.MainActivity -e url https://HOST:8443/?agent=vhum
 */
public class MainActivity extends Activity {
    static final String DEFAULT_URL = "https://your-server:8443/?agent=vhum";   // the teach server (tools/teach_server.py); typed in the app
    private WebView web;
    private PermissionRequest pending;
    private String host;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        String url = getIntent().getStringExtra("url");
        if (url == null || url.isEmpty()) url = DEFAULT_URL;
        host = Uri.parse(url).getHost();
        web = new WebView(this);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        web.setWebViewClient(new WebViewClient() {
            @Override
            public void onReceivedSslError(WebView view, SslErrorHandler handler, SslError error) {
                String h = Uri.parse(error.getUrl()).getHost();
                if (h != null && h.equals(host)) handler.proceed(); else handler.cancel();
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(PermissionRequest request) {
                if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
                    request.grant(new String[]{PermissionRequest.RESOURCE_AUDIO_CAPTURE});
                } else {
                    pending = request;
                    requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, 1);
                }
            }
        });
        setContentView(web);
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, 1);
        }
        web.loadUrl(url);
    }

    @Override
    public void onRequestPermissionsResult(int code, String[] perms, int[] results) {
        if (pending != null) {
            if (results.length > 0 && results[0] == PackageManager.PERMISSION_GRANTED) {
                pending.grant(new String[]{PermissionRequest.RESOURCE_AUDIO_CAPTURE});
            } else {
                pending.deny();
            }
            pending = null;
        }
    }

    @Override
    public void onBackPressed() {
        if (web.canGoBack()) web.goBack(); else super.onBackPressed();
    }
}
