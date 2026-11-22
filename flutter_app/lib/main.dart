import 'package:flutter/material.dart';

import 'app.dart';
import 'state/app_controller.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(UdbExpressiveApp(controller: AppController()));
}
